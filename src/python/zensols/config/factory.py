"""Classes that create new instances of classes from application configuration
objects and files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Union, Type, Optional
from abc import ABC, abstractmethod
from enum import Enum
import types
import logging
import inspect
import re
import copy as cp
from time import time
from zensols.util import APIError
from zensols.introspect import ClassImporter
from zensols.config import Configurable
from zensols.persist import persisted, PersistedWork, Deallocatable

logger = logging.getLogger(__name__)


class RedefinedInjectionError(APIError):
    """Raised when any attempt to redefine or reuse injections for a class
    """
    pass


class FactoryError(APIError):
    """Raised when an object can not be instantianted by a :class:`.ConfigFactory`.

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
        """Return a fully qualified class name string for class ``cls``.

        """
        return ClassImporter.full_classname(cls)

    def find_class(self, class_name: str) -> Type:
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

    def find_class(self, class_name: str) -> Type:
        classes = {}
        classes.update(globals())
        classes.update(self.instance_classes)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'looking up class: {class_name}')
        if class_name not in classes:
            raise FactoryError(
                f'class {class_name} is not registered in factory {self}')
        cls = classes[class_name]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'found class: {cls}')
        return cls


class FactoryClassImporter(ClassImporter):
    """Just like the super class, but if instances of type
    :class:`.FactoryStateObserver` are notified with a
    :class:`.FactoryState.CREATED`.

    """
    def _bless(self, inst: Any) -> Any:
        if isinstance(inst, FactoryStateObserver):
            inst._notify_state(FactoryState.CREATED)
        return super()._bless(inst)


class ImportClassResolver(ClassResolver):
    """Resolve a class name from a list of registered class names without the
    module part.  This is used with the ``register`` method on
    :class:`.ConfigFactory`.

    :see: :meth:`.ConfigFactory.register`

    """
    def __init__(self, reload: bool = False):
        self.reload = reload

    def create_class_importer(self, class_name: str):
        return FactoryClassImporter(class_name, reload=self.reload)

    def find_class(self, class_name: str):
        class_importer = self.create_class_importer(class_name)
        return class_importer.get_module_class()[1]


class ConfigFactory(object):
    """Creates new instances of classes and configures them given data in a
    configuration :class:`.Configurable` instance.

    """
    NAME_ATTRIBUTE = 'name'
    """The *name* of the parameter given to ``__init__``.  If a parameter of this
    name is on the instance being created it will be set from the name of the
    section.

    """

    CONFIG_ATTRIBUTE = 'config'
    """The *configuration* of the parameter given to ``__init__``.  If a parameter
    of this name is on the instance being created it will be set as the
    instance of the configuration given to the initializer of this factory
    instance.

    """

    CONIFG_FACTORY_ATTRIBUTE = 'config_factory'
    """The *configuration factory* of the parameter given to ``__init__``.  If a
    parameter of this name is on the instance being created it will be set as
    the instance of this configuration factory.

    """

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
            self.class_resolver = DictionaryClassResolver(
                self.INSTANCE_CLASSES)
        else:
            self.class_resolver = class_resolver

    @classmethod
    def register(cls, instance_class: Type, name: str = None):
        """Register a class with the factory.  This method assumes the factory instance
        was created with a (default) :class:`.DictionaryClassResolver`.

        :param instance_class: the class to register with the factory (not a
                               string)

        :param name: the name to use as the key for instance class lookups;
                     defaults to the name of the class

        """
        if name is None:
            name = instance_class.__name__
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'registering: {instance_class} for {cls} -> {name}')
        cls.INSTANCE_CLASSES[name] = instance_class

    def _find_class(self, class_name: str) -> Type:
        """Resolve the class from the name."""
        return self.class_resolver.find_class(class_name)

    def _class_name_params(self, name: str):
        """Get the class name and parameters to use for ``__init__``."""
        sec = self.pattern.format(**{'name': name})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'section: {sec}')
        params = {}
        try:
            params.update(self.config.populate({}, section=sec))
        except Exception as e:
            logger.error(f'can not populate from section {sec}: {e}')
            raise e
        class_name = params.get('class_name')
        if class_name is None:
            if len(params) == 0:
                raise FactoryError(f'no such entry: \'{name}\'')
            else:
                class_name = 'zensols.config.Settings'
        else:
            del params['class_name']
        return class_name, params

    def _has_init_parameter(self, cls: Type, param_name: str):
        args = inspect.signature(cls.__init__)
        return param_name in args.parameters

    def _instance(self, cls_desc: str, cls: Type, *args, **kwargs):
        """Return the instance.

        :param cls_desc: a description of the class (i.e. section name)

        :param cls: the class to create the instance from

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'args: {args}, kwargs: {kwargs}')
        try:
            if logger.isEnabledFor(logging.DEBUG):
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

    def instance(self, name: Optional[str] = None, *args, **kwargs):
        """Create a new instance using key ``name``.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class; this is the section name for
                     the :class:`.ImportConfigFactory`

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'new instance of {name}')
        t0 = time()
        name = self.default_name if name is None else name
        if logger.isEnabledFor(logging.DEBUG):
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
        if logger.isEnabledFor(logging.DEBUG):
            for k, v in params.items():
                logger.debug(f'populating {k} -> {v} ({type(v)})')
        inst = self._instance(name, cls, *args, **params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'created {name} instance of {cls.__name__} ' +
                         f'in {(time() - t0):.2f}s')
        return inst

    def get_class(self, name: str) -> Type:
        """Return a class by name.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class; this is the section name for
                     the :class:`.ImportConfigFactory`
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'new instance of {name}')
        name = self.default_name if name is None else name
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance of {name}')
        class_name, params = self._class_name_params(name)
        return self._find_class(class_name)

    def from_config_string(self, v: str) -> Any:
        """Create an instance from a string used as option values in the configuration.

        """
        try:
            v = eval(v)
        except Exception:
            pass
        return self.instance(v)

    def clone(self) -> Any:
        """Return a copy of this configuration factory that functionally works the
        same.

        """
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
    """The ``instance`` regular expression used to identify children attributes to
    set on the object.  The process if creation can chain from parent to
    children recursively.

    """

    _INJECTS = {}
    """Track injections to fail on any attempts to redefine."""

    def __init__(self, *args, reload: Optional[bool] = False,
                 shared: Optional[bool] = True,
                 reload_pattern: Optional[Union[re.Pattern, str]] = None,
                 **kwargs):
        """Initialize the configuration factory.

        :param reload: whether or not to reload the module when resolving the
                       class, which is useful for debugging in a REPL

        :param shared: when ``True`` instances are shared and only created
                        once across sections for the life of this
                        ``ImportConfigFactory`` instance

        :param reload_pattern: if set, reload classes that have a fully
                               qualified name that match the regular expression
                               regarless of the setting ``reload``

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating import config factory, reload: {reload}')
        super().__init__(*args, **kwargs, class_resolver=ImportClassResolver())
        self._set_reload(reload)
        if shared:
            self._shared = {}
        else:
            self._shared = None
        self.shared = shared
        if isinstance(reload_pattern, str):
            self.reload_pattern = re.compile(reload_pattern)
        else:
            self.reload_pattern = reload_pattern

    def __getstate__(self):
        state = dict(self.__dict__)
        state['_shared'] = None if self._shared is None else {}
        del state['class_resolver']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.class_resolver = ImportClassResolver()

    def clear(self):
        """Clear any shared instances.

        """
        if self._shared is not None:
            self._shared.clear()

    def clear_instance(self, name: str):
        """Remove a shared (cached) object instance.

        """
        if self._shared is not None:
            return self._shared.pop(name, None)

    def clone(self) -> Any:
        """Return a copy of this configuration factory that functionally works the
        same.  However, it does not copy over any resources generated during
        the life of the factory.

        """
        clone = super().clone()
        clone.clear()
        return clone

    def deallocate(self):
        super().deallocate()
        if self._shared is not None:
            for v in self._shared.values():
                if isinstance(v, Deallocatable):
                    v.deallocate()
            self._shared.clear()

    def instance(self, name: str = None, *args, **kwargs):
        if self._shared is None:
            inst = super().instance(name, *args, **kwargs)
        else:
            inst = self._shared.get(name)
            if inst is None:
                inst = super().instance(name, *args, **kwargs)
                self._shared[name] = inst
        return inst

    def new_instance(self, name: str = None, *args, **kwargs):
        """Create a new instance without it being shared.  This only does something
        different from :meth:`instance` if this is a shared instance factory
        ith ``shared=True`` given to the initializer.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        :see: :meth:`instance`

        """
        inst = self.instance(name, *args, **kwargs)
        self.clear_instance(name)
        return inst

    def _set_reload(self, reload: bool):
        self.reload = reload
        self.class_resolver.reload = reload

    def _attach_persistent(self, inst: Any, name: str, kwargs: Dict[str, str]):
        persist = persisted(**kwargs)
        new_meth = persist(lambda self: getattr(inst, name))
        new_meth = types.MethodType(new_meth, inst)
        setattr(inst, name, new_meth)

    def _create_instance(self, section: str, config_params: Dict[str, str],
                         params: Dict[str, Any]) -> Any:
        secs = self.config.serializer.parse_object(section)
        if isinstance(secs, (tuple, list)):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'list instance: {type(secs)}')
            inst = list(map(lambda s: self.instance(s, **params), secs))
            if isinstance(secs, tuple):
                inst = tuple(inst)
        elif isinstance(secs, dict):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'dict instance: {type(secs)}')
            inst = {}
            for k, v in secs.items():
                v = self.instance(v, **params)
                inst[k] = v
        elif isinstance(secs, str):
            inst = self.instance(secs, **params)
        else:
            raise FactoryError(f'unknown instance type {type(secs)}: {secs}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance in section {section} ' +
                         f'with {params}, config: {config_params}')
        return inst

    def _populate_instances(self, pconfig: str, section: str):
        child_params = {}
        reload = False
        defined_directives = set('param reload type'.split())
        inst_conf = None
        if pconfig is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'parsing param config: {pconfig}')
            inst_conf = eval(pconfig)
            unknown = set(inst_conf.keys()) - defined_directives
            if len(unknown) > 0:
                raise FactoryError(f'unknown directive(s): {unknown}')
            if 'param' in inst_conf:
                cparams = inst_conf['param']
                cparams = self.config.serializer.populate_state(cparams, {})
                child_params.update(cparams)
            if 'reload' in inst_conf:
                reload = inst_conf['reload']
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'setting reload: {reload}')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'applying param config: {inst_conf}')
        self._set_reload(reload)
        return self._create_instance(section, inst_conf, child_params)

    def from_config_string(self, v: str) -> Any:
        """Create an instance from a string that looks like :obj:`CHILD_REGEXP` used as
        option values in the configuration.

        """
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
                    raise FactoryError(f"no property '{prop_name}' found '" +
                                       f"in section '{sec_name}'")
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'import instance: section name: {sec_name}, ' +
                         f'cls={class_name}, args={args}, kwargs={kwargs}')
        pw_injects = self._process_injects(sec_name, kwargs)
        prev_defined_sec = self._INJECTS.get(class_name)

        if prev_defined_sec is not None and prev_defined_sec != sec_name:
            # fail when redefining injections, and thus class metadata,
            # configuration
            msg = ('attempt redefine or reuse injection for class ' +
                   f'{class_name} in section {sec_name} previously ' +
                   f'defined in section {prev_defined_sec}')
            raise RedefinedInjectionError(msg)

        if len(pw_injects) > 0 and class_name not in self._INJECTS:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'sec assign {sec_name} = {class_name}')
            self._INJECTS[class_name] = sec_name

        initial_reload = self.reload
        reload = self.reload
        if self.reload_pattern is not None:
            m = self.reload_pattern.match(class_name)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'class {class_name} matches reload pattern ' +
                             f'{self.reload_pattern}: {m}')
            reload = m is not None
        try:
            self._set_reload(reload)
            if reload:
                # we still have to reload at the top level (root in the
                # instance graph)
                cresolver: ClassResolver = self.class_resolver
                class_importer = cresolver.create_class_importer(class_name)
                inst = class_importer.instance(*args, **kwargs)
                reset_props = True
            else:
                inst = super()._instance(sec_name, cls, *args, **kwargs)
        finally:
            self._set_reload(initial_reload)

        cls = inst.__class__

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding injects: {len(pw_injects)}')
        for pw_name, prop_name, inject in pw_injects:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'inject: {pw_name}, {prop_name}, {inject}')
            init_val = inject.pop('initial_value')
            pw = PersistedWork(owner=inst, **inject)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'set: {pw.is_set()}: {pw}')
            if not pw.is_set():
                pw.set(init_val)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'setting member {pw_name}={pw} on {cls}')
            setattr(inst, pw_name, pw)
            if reset_props or not hasattr(cls, prop_name):
                logger.debug(f'setting property {prop_name}={pw_name}')
                getter = eval(f"lambda s: getattr(s, '{pw_name}')()")
                setter = eval(f"lambda s, v: hasattr(s, '{pw_name}') " +
                              f"and getattr(s, '{pw_name}').set(v)")
                prop = property(getter, setter)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'set property: {prop}')
                setattr(cls, prop_name, prop)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'create instance {cls}')
        return inst
