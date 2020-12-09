"""Classes that create new instances of classes from application configuration
objects and files.

"""
__author__ = 'Paul Landes'

from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from enum import Enum
import types
import logging
import inspect
import importlib
import re
import copy as cp
from functools import reduce
from time import time
from zensols.config import Configurable
from zensols.persist import persisted, PersistedWork, Deallocatable

logger = logging.getLogger(__name__)


class RedefinedInjectionError(ValueError):
    """Raised when any attempt to redefine or reuse injections for a class
    """
    pass


class FactoryState(Enum):
    """The state updated from an instance of :class:`.ConfigFactory`.  Currently
    the only state is that an object has finished being created.

    Future states might inlude when a :class:`.ImportConfigFactory` has created
    all objects from a configuration shared session.

    """
    CREATED = 1


class FactoryStateObserver(ABC):
    """An interface that recieves notifications that the factory has created this
    instance.  This is useful for classes such as :class:`.Writeback`.

    :see: :class:`.Writeback`

    """
    @abstractmethod
    def _notify_state(self, state: FactoryState):
        pass


class ClassResolver(ABC):
    """Used to resolve a class from a string.

    """
    @staticmethod
    def full_classname(cls: type) -> str:
        module = cls.__module__
        if module is None or module == str.__class__.__module__:
            return cls.__name__
        else:
            return module + '.' + cls.__name__

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
        pkg_s = pkg.split('.')
        mod = reduce(lambda m, n: getattr(m, n), pkg_s[1:], __import__(pkg))
        logger.debug(f'mod: {mod}, reloading: {self.reload}')
        if self.reload:
            logger.debug(f'reload: cls: {mod}, {cname}')
            mod = importlib.reload(mod)
        if not hasattr(mod, cname):
            raise ValueError(f"no class '{cname}' found in module '{mod}'")
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
            logger.debug(f'class importer creating instance of {cls}')
            inst = cls(*args, **kwargs)
            if isinstance(inst, FactoryStateObserver):
                inst._notify_state(FactoryState.CREATED)
        except Exception as e:
            msg = f'can not instantiate {cls}({args}, {kwargs})'
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

    def create_class_importer(self, class_name):
        return ClassImporter(class_name, reload=self.reload)

    def find_class(self, class_name):
        class_importer = self.create_class_importer(class_name)
        return class_importer.get_module_class()[1]


class ConfigFactory(object):
    """Creates new instances of classes and configures them given data in a
    configuration ``Configurable`` instance.

    """
    NAME_ATTRIBUTE = 'name'
    CONFIG_ATTRIBUTE = 'config'
    CONIFG_FACTORY_ATTRIBUTE = 'config_factory'

    def __init__(self, config: Configurable, pattern: str = '{name}',
                 default_name: str = 'default',
                 class_resolver: ClassResolver = None):
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
        self.default_name = default_name
        if class_resolver is None:
            self.class_resolver = DictionaryClassResolver(self.INSTANCE_CLASSES)
        else:
            self.class_resolver = class_resolver

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
        return self.class_resolver.find_class(class_name)

    def _class_name_params(self, name):
        "Get the class name and parameters to use for ``__init__``."
        sec = self.pattern.format(**{'name': name})
        logger.debug(f'section: {sec}')
        params = {}
        try:
            params.update(self.config.populate({}, section=sec))
        except Exception as e:
            logger.error(f'can not populate from section {sec}: {e}')
            raise e
        class_name = params.get('class_name')
        if class_name is None:
            raise ValueError(f'no class_name parameter for \'{name}\'')
        del params['class_name']
        return class_name, params

    def _has_init_parameter(self, cls, param_name):
        args = inspect.signature(cls.__init__)
        return param_name in args.parameters

    def _instance(self, cls_desc, cls, *args, **kwargs):
        """Return the instance.

        :param cls: the class to create the instance from
        :param args: given to the ``__init__`` method
        :param kwargs: given to the ``__init__`` method
        """
        logger.debug(f'args: {args}, kwargs: {kwargs}')
        try:
            logger.debug(f'config factory creating instance of {cls}')
            inst = cls(*args, **kwargs)
            if isinstance(inst, FactoryStateObserver):
                inst._notify_state(FactoryState.CREATED)
        except Exception as e:
            logger.error(f'can not create \'{cls_desc}\' for class ' +
                         f'{cls}({args})({kwargs}): {e}')
            raise e
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'inst: {inst.__class__}')
        return inst

    def instance(self, name: Type = None, *args, **kwargs):
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
        if self._has_init_parameter(cls, self.CONFIG_ATTRIBUTE):
            logger.debug('found config parameter')
            params['config'] = self.config
        if self._has_init_parameter(cls, self.NAME_ATTRIBUTE):
            logger.debug('found name parameter')
            params['name'] = name
        if self._has_init_parameter(cls, self.CONIFG_FACTORY_ATTRIBUTE):
            logger.debug('found config factory parameter')
            params['config_factory'] = self
        if logger.level >= logging.DEBUG:
            for k, v in params.items():
                logger.debug(f'populating {k} -> {v} ({type(v)})')
        inst = self._instance(name, cls, *args, **params)
        logger.info(f'created {name} instance of {cls.__name__} ' +
                    f'in {(time() - t0):.2f}s')
        return inst

    def from_config_string(self, v: str) -> Any:
        try:
            v = eval(v)
        except Exception:
            pass
        return self.instance(v)

    def clone(self) -> Any:
        return cp.copy(self)

    def __call__(self, *args, **kwargs):
        """Calls ``instance``.

        """
        return self.instance(*args, **kwargs)


class ImportConfigFactory(ConfigFactory, Deallocatable):
    """Import a class by the fully qualified class name (includes the module).

    This is a convenience class for setting the parent class ``class_resolver``
    parameter.

    """
    CHILD_REGEXP = re.compile(r'^instance(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    # track injections to fail on any attempts to redefine
    INJECTS = {}

    def __init__(self, *args, reload: bool = False, shared: bool = True,
                 reload_root=None, **kwargs):
        """Initialize the configuration factory.

        :param reload: whether or not to reload the module when resolving the
                       class, which is useful for debugging in a REPL

        :param shared: when ``True`` instances are shared and only created
                        once across sections for the life of this
                        ``ImportConfigFactory`` instance

        :param reload_root: when ``True``, only reload the module of the class
                            from the configuration indicated in
                            :meth:`instance` rather than following the instance
                            dependency tree

        """
        logger.debug(f'creating import config factory with reload: {reload}')
        super().__init__(*args, **kwargs, class_resolver=ImportClassResolver())
        self._set_reload(reload)
        if shared:
            self.shared = {}
        else:
            self.shared = None
        self.reload_root = reload_root if reload_root is not None else reload

    def __getstate__(self):
        state = dict(self.__dict__)
        state['shared'] = None if self.shared is None else {}
        del state['class_resolver']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.class_resolver = ImportClassResolver()

    def clear(self):
        """Clear any shared instances.

        """
        if self.shared is not None:
            self.shared.clear()

    def clear_instance(self, name: str):
        """Remove a shared (cached) object instance.

        """
        if self.shared is not None:
            return self.shared.pop(name, None)

    def clone(self) -> Any:
        clone = super().clone()
        clone.clear()
        return clone

    def deallocate(self):
        super().deallocate()
        if self.shared is not None:
            for v in self.shared.values():
                if isinstance(v, Deallocatable):
                    v.deallocate()
            self.shared.clear()

    def instance(self, name=None, *args, **kwargs):
        if self.shared is None:
            inst = super().instance(name, *args, **kwargs)
        else:
            inst = self.shared.get(name)
            if inst is None:
                inst = super().instance(name, *args, **kwargs)
                self.shared[name] = inst
        return inst

    def _set_reload(self, reload: bool):
        self.reload = reload
        self.class_resolver.reload = reload

    def _attach_persistent(self, inst: Any, name: str, kwargs: Dict[str, str]):
        persist = persisted(**kwargs)
        new_meth = persist(lambda self: getattr(inst, name))
        new_meth = types.MethodType(new_meth, inst)
        setattr(inst, name, new_meth)

    def _populate_instances(self, pconfig: str, section: str):
        child_params = {}
        reload = False
        defined_directives = set('param reload'.split())
        if pconfig is not None:
            logger.debug(f'parsing param config: {pconfig}')
            pconfig = eval(pconfig)
            unknown = set(pconfig.keys()) - defined_directives
            if len(unknown) > 0:
                raise ValueError(f'unknown directive(s): {unknown}')
            if 'param' in pconfig:
                cparams = pconfig['param']
                cparams = self.config.serializer.populate_state(cparams, {})
                child_params.update(cparams)
            if 'reload' in pconfig:
                reload = pconfig['reload']
                logger.debug(f'setting reload: {reload}')
            logger.debug(f'applying param config: {pconfig}')
        logger.debug(f'creating instance in section {section}')
        self._set_reload(reload)
        return self.instance(section, **child_params)

    def from_config_string(self, v: str) -> Any:
        m = self.CHILD_REGEXP.match(v)
        if m:
            pconfig, section = m.groups()
            v = self._populate_instances(pconfig, section)
        return v

    def _class_name_params(self, name):
        class_name, params = super()._class_name_params(name)
        insts = {}
        initial_reload = self.reload
        try:
            for k, v in params.items():
                if isinstance(v, str):
                    m = self.CHILD_REGEXP.match(v)
                    if m:
                        pconfig, section = m.groups()
                        insts[k] = self._populate_instances(pconfig, section)
        finally:
            self._set_reload(initial_reload)
        params.update(insts)
        return class_name, params

    def _process_injects(self, sec_name, kwargs):
        pname = 'injects'
        pw_param_set = kwargs.get(pname)
        props = []
        if pw_param_set is not None:
            del kwargs[pname]
            for params in eval(pw_param_set):
                params = dict(params)
                prop_name = params['name']
                del params['name']
                pw_name = f'_{prop_name}_pw'
                params['path'] = pw_name
                if prop_name not in kwargs:
                    raise ValueError(f"no property '{prop_name}' found in '" +
                                     f"section '{sec_name}'")
                params['initial_value'] = kwargs[prop_name]
                # don't delete the key here so that the type can be defined for
                # dataclasses, effectively as documentation
                #
                # del kwargs[prop_name]
                props.append((pw_name, prop_name, params))
        return props

    def _instance(self, cls_desc, cls, *args, **kwargs):
        sec_name = cls_desc
        reset_props = False
        class_name = ClassResolver.full_classname(cls)
        logger.debug(f'import instance: section name: {sec_name}, ' +
                     f'cls={class_name}, args={args}, kwargs={kwargs}')
        pw_injects = self._process_injects(sec_name, kwargs)
        prev_defined_sec = self.INJECTS.get(class_name)

        if prev_defined_sec is not None and prev_defined_sec != sec_name:
            # fail when redefining injections, and thus class metadata,
            # configuration
            msg = ('attempt redefine or reuse injection for class ' +
                   f'{class_name} in section {sec_name} previously ' +
                   f'defined in section {prev_defined_sec}')
            raise RedefinedInjectionError(msg)

        if len(pw_injects) > 0 and class_name not in self.INJECTS:
            logger.debug(f'sec assign {sec_name} = {class_name}')
            self.INJECTS[class_name] = sec_name

        initial_reload = self.reload
        try:
            self._set_reload(self.reload_root)
            if self.reload:
                # we still have to reload at the top level (root in the instance
                # graph)
                class_resolver = self.class_resolver
                class_importer = class_resolver.create_class_importer(class_name)
                inst = class_importer.instance(*args, **kwargs)
                reset_props = True
            else:
                inst = super()._instance(sec_name, cls, *args, **kwargs)
        finally:
            self._set_reload(initial_reload)

        cls = inst.__class__

        logger.debug(f'adding injects: {len(pw_injects)}')
        for pw_name, prop_name, inject in pw_injects:
            logger.debug(f'inject: {pw_name}, {prop_name}, {inject}')
            init_val = inject.pop('initial_value')
            pw = PersistedWork(owner=inst, **inject)
            logger.debug(f'set: {pw.is_set()}: {pw}')
            if not pw.is_set():
                pw.set(init_val)
            logger.debug(f'setting member {pw_name}={pw} on {cls}')
            setattr(inst, pw_name, pw)
            if reset_props or not hasattr(cls, prop_name):
                logger.debug(f'setting property {prop_name}={pw_name}')
                getter = eval(f"lambda s: getattr(s, '{pw_name}')()")
                setter = eval(f"lambda s, v: hasattr(s, '{pw_name}') and getattr(s, '{pw_name}').set(v)")
                prop = property(getter, setter)
                logger.debug(f'set property: {prop}')
                setattr(cls, prop_name, prop)
        logger.debug(f'create instance {cls}')
        return inst
