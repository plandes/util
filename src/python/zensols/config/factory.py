import logging
from abc import ABC
from typing import Dict
import inspect
import importlib
import re
from functools import reduce
from time import time
from zensols.config import Configurable

logger = logging.getLogger(__name__)


class ClassResolver(ABC):
    """Used to resolve a class from a string.

    """
    def find_class(self, class_name: str) -> type:
        """Return a class given the name of the class.

        :param class_name: represents the class name, which might or might not
                           have the module as part of that name

        """
        pass


class DictionaryClassResolver(ClassResolver):
    """Resolve a class name from a list of registered class names without the
    module part.  This is used with the ``register`` method on
    ``ConfigFactory``.

    :see: ConfigFactory.register
    """
    def __init__(self, instance_classes: Dict[str, type]):
        self.instance_classes = instance_classes

    def find_class(self, class_name):
        classes = {}
        classes.update(globals())
        classes.update(self.instance_classes)
        logger.debug(f'looking up class: {class_name}')
        if class_name not in classes:
            raise ValueError(
                f'class {class_name} is not registered in factory {self}')
        cls = classes[class_name]
        logger.debug(f'found class: {cls}')
        return cls


class ClassImporter(object):
    """Utility class that reloads a module and instantiates a class from a string
    class name.  This is handy for prototyping code in a Python REPL.

    """
    CLASS_REGEX = re.compile(r'^(.+)\.(.+?)$')

    def __init__(self, class_name: str, reload: bool = True):
        """Initialize with the class name.

        :param class_name: the fully qualifed name of the class (including the
                           module portion of the class name)
        :param reload: if ``True`` then reload the module before returning the
        class
        """
        self.class_name = class_name
        self.reload = reload

    def parse_module_class(self):
        """Parse the module and class name part of the fully qualifed class name.
        """

        cname = self.class_name
        match = re.match(self.CLASS_REGEX, cname)
        if not match:
            raise ValueError(f'not a fully qualified class name: {cname}')
        return match.groups()

    def get_module_class(self):
        """Return the module and class as a tuple of the given class in the
        initializer.

        :param reload: if ``True`` then reload the module before returning the
        class

        """
        pkg, cname = self.parse_module_class()
        logger.debug(f'pkg: {pkg}, class: {cname}')
        pkg = pkg.split('.')
        mod = reduce(lambda m, n: getattr(m, n), pkg[1:], __import__(pkg[0]))
        logger.debug(f'mod: {mod}, reloading: {self.reload}')
        if self.reload:
            importlib.reload(mod)
        cls = getattr(mod, cname)
        logger.debug(f'class: {cls}')
        return mod, cls

    def instance(self, *args, **kwargs):
        """Create an instance of the specified class in the initializer.

        :param args: the arguments given to the initializer of the new class
        :param kwargs: the keyword arguments given to the initializer of the
                     new class

        """
        mod, cls = self.get_module_class()
        try:
            inst = cls(*args, **kwargs)
        except Exception as e:
            msg = f'could not instantiate {cls}({args}, {kwargs})'
            logger.error(msg, e)
            raise e
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'inst: {inst}')
        return inst

    def set_log_level(self, level=logging.INFO):
        """Convenciene method to set the log level of the module given in the
        initializer of this class.

        :param level: and instance of ``logging.<level>``
        """
        mod, cls = self.parse_module_class()
        logging.getLogger(mod).setLevel(level)


class ImportClassResolver(ClassResolver):
    """Resolve a class name from a list of registered class names without the
    module part.  This is used with the ``register`` method on
    ``ConfigFactory``.

    :see: ConfigFactory.register
    """
    def __init__(self, reload: bool = False):
        self.reload = reload

    def find_class(self, class_name):
        class_importer = ClassImporter(class_name, reload=self.reload)
        return class_importer.get_module_class()[1]


class ConfigFactory(object):
    """Creates new instances of classes and configures them given data in a
    configuration ``Configurable`` instance.

    """
    def __init__(self, config: Configurable, pattern: str = '{name}',
                 config_param_name: str = 'config',
                 name_param_name: str = 'name', default_name: str = 'default',
                 class_importer: ClassImporter = None):
        """Initialize a new factory instance.

        :param config: the configuration used to create the instance; all data
                       from the corresponding section is given to the
                       ``__init__`` method
        :param pattern: section pattern used to find the values given to the
                        ``__init__`` method
        :param config_param_name: the ``__init__`` parameter name used for the
                                  configuration object given to the factory's
                                  ``instance`` method; defaults to ``config``
        :param config_param_name: the ``__init__`` parameter name used for the
                                  instance name given to the factory's
                                  ``instance`` method; defaults to ``name``

        """
        self.config = config
        self.pattern = pattern
        self.config_param_name = config_param_name
        self.name_param_name = name_param_name
        self.default_name = default_name
        if class_importer is None:
            self.class_importer = DictionaryClassResolver(self.INSTANCE_CLASSES)
        else:
            self.class_importer = class_importer

    @classmethod
    def register(cls, instance_class, name=None):
        """Register a class with the factory.  This method assumes the factory instance
        was created with a (default) ``DictionaryClassResolver``.

        :param instance_class: the class to register with the factory (not a
                               string)
        :param name: the name to use as the key for instance class lookups;
                     defaults to the name of the class

        """
        if name is None:
            name = instance_class.__name__
        logger.debug(f'registering: {instance_class} for {cls} -> {name}')
        cls.INSTANCE_CLASSES[name] = instance_class

    def _find_class(self, class_name):
        "Resolve the class from the name."
        return self.class_importer.find_class(class_name)

    def _class_name_params(self, name):
        "Get the class name and parameters to use for ``__init__``."
        sec = self.pattern.format(**{'name': name})
        logger.debug(f'section: {sec}')
        params = {}
        params.update(self.config.populate({}, section=sec))
        class_name = params['class_name']
        del params['class_name']
        return class_name, params

    def _has_init_config(self, cls):
        """Return whether the class has a ``config`` parameter in the ``__init__``
        method.

        """
        args = inspect.signature(cls.__init__)
        return self.config_param_name in args.parameters

    def _has_init_name(self, cls):
        """Return whether the class has a ``name`` parameter in the ``__init__``
        method.

        """
        args = inspect.signature(cls.__init__)
        return self.name_param_name in args.parameters

    def _instance(self, cls, *args, **kwargs):
        """Return the instance.

        :param cls: the class to create the instance from
        :param args: given to the ``__init__`` method
        :param kwargs: given to the ``__init__`` method
        """
        logger.debug(f'args: {args}, kwargs: {kwargs}')
        try:
            return cls(*args, **kwargs)
        except Exception as e:
            logger.error(f'couldnt not create class {cls}({args})({kwargs}): {e}')
            raise e

    def instance(self, name=None, *args, **kwargs):
        """Create a new instance using key ``name``.

        :param name: the name of the class (by default) or the key name of the
            class used to find the class
        :param args: given to the ``__init__`` method
        :param kwargs: given to the ``__init__`` method

        """
        logger.info(f'new instance of {name}')
        t0 = time()
        name = self.default_name if name is None else name
        logger.debug(f'creating instance of {name}')
        class_name, params = self._class_name_params(name)
        cls = self._find_class(class_name)
        params.update(kwargs)
        if self._has_init_config(cls):
            logger.debug(f'found config parameter')
            params['config'] = self.config
        if self._has_init_name(cls):
            logger.debug(f'found name parameter')
            params['name'] = name
        if logger.level >= logging.DEBUG:
            for k, v in params.items():
                logger.debug(f'populating {k} -> {v} ({type(v)})')
        inst = self._instance(cls, *args, **params)
        logger.info(f'created {name} instance of {cls.__name__} ' +
                    f'in {(time() - t0):.2f}s')
        return inst


class ImportConfigFactory(ConfigFactory):
    """Import a class by the fully qualified class name (includes the module).

    This is a convenience class for setting the parent class ``class_importer``
    parameter.

    """
    CHILD_REGEXP = re.compile(r'^instance:\s*(.+)$')

    def __init__(self, *args, reload: bool = False, **kwargs):
        """Initialize the configuration factory.

        :param reload: whether or not to reload the module when resolving the
                       class, which is useful for debugging in a REPL

        """
        logger.debug(f'creating import config factory with reload: {reload}')
        class_importer = ImportClassResolver(reload=reload)
        super(ImportConfigFactory, self).__init__(
            *args, **kwargs, class_importer=class_importer)

    def _class_name_params(self, name):
        class_name, params = super(ImportConfigFactory, self).\
            _class_name_params(name)
        insts = {}
        for k, v in params.items():
            if isinstance(v, str):
                m = self.CHILD_REGEXP.match(v)
                if m:
                    section = m.group(1)
                    insts[k] = self.instance(section)
        params.update(insts)
        return class_name, params


class ConfigChildrenFactory(ConfigFactory):
    """Like ``ConfigFactory``, but create children defined with the configuration
    key ``CREATE_CHILDREN_KEY``.  For each of these defined in the comma
    separated property child property is set and then passed on to the
    initializer of the object created.

    In addition, any parameters passed to the initializer of the instance
    method are passed on the comma separate list ``<name>_pass_param`` where
    ``name`` is the name of the next object to instantiate per the
    configuraiton.

    """
    CREATE_CHILDREN_KEY = 'create_children'

    def _process_pass_params(self, name, kwargs):
        passkw = {}
        kname = f'{name}_pass_param'
        if kname in kwargs:
            for k in kwargs[kname].split(','):
                logger.debug(f'passing parameter {k}')
                passkw[k] = kwargs[k]
            del kwargs[kname]
        return passkw

    def _instance_children(self, kwargs):
        if self.CREATE_CHILDREN_KEY in kwargs:
            for k in kwargs[self.CREATE_CHILDREN_KEY].split(','):
                passkw = self._process_pass_params(k, kwargs)
                logger.debug(f'create {k}: {kwargs}')
                if k in kwargs:
                    kwargs[k] = self.instance(kwargs[k], **passkw)
                    for pk in passkw.keys():
                        del kwargs[pk]
            del kwargs[self.CREATE_CHILDREN_KEY]

    def _instance(self, cls, *args, **kwargs):
        logger.debug(f'stash create: {cls}({args})({kwargs})')
        self._instance_children(kwargs)
        return super(ConfigChildrenFactory, self)._instance(
            cls, *args, **kwargs)


class CachingConfigFactory(object):
    """Just like ``ConfigFactory`` but caches instances in memory by name.

    """
    def __init__(self, delegate: ConfigFactory):
        """Initialize.

        :param delegate: the delegate factory to use for the actual instance
            creation

        """
        self.delegate = delegate
        self.insts = {}

    def instance(self, name=None, *args, **kwargs):
        logger.debug(f'cache config instance for {name}')
        if name in self.insts:
            logger.debug(f'reusing cached instance of {name}')
            return self.insts[name]
        else:
            logger.debug(f'creating new instance of {name}')
            inst = self.delegate.instance(name, *args, **kwargs)
            self.insts[name] = inst
            return inst

    def load(self, name=None, *args, **kwargs):
        if name in self.insts:
            logger.debug(f'reusing (load) cached instance of {name}')
            return self.insts[name]
        else:
            logger.debug(f'load new instance of {name}')
            inst = self.delegate.load(name, *args, **kwargs)
            self.insts[name] = inst
            return inst

    def exists(self, name: str):
        return self.delegate.exists(name)

    def dump(self, name: str, inst):
        self.delegate.dump(name, inst)

    def delete(self, name):
        self.delegate.delete(name)
        self.evict(name)

    def evict(self, name):
        if name in self.insts:
            del self.insts[name]

    def evict_all(self):
        self.insts.clear()
