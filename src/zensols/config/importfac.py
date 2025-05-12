"""A configuration factory that (re)imports based on class name.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
import typing
from typing import (
    Tuple, Dict, Optional, Union, Any, Type, Iterable, Callable, ClassVar, Set
)
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
import dataclasses
import logging
import types
import re
from frozendict import frozendict
from zensols.introspect import ClassResolver, ClassImporter
from zensols.persist import persisted, PersistedWork, Deallocatable
from . import (
    Settings, Dictable, FactoryError, Configurable,
    ImportClassResolver, ConfigFactory,
)

logger = logging.getLogger(__name__)


class RedefinedInjectionError(FactoryError):
    """Raised when any attempt to redefine or reuse injections for a class.

    """
    pass


@dataclass
class ModulePrototype(Dictable):
    """Contains the prototype information necessary to create an object instance
    using :class:`.ImportConfigFactoryModule.

    """
    _DICTABLE_ATTRIBUTES: ClassVar[Set[str]] = {'params', 'config'}

    _CHILD_PARAM_DIRECTIVES: ClassVar[Set[str]] = frozenset(
        'param reload type share'.split())
    """The set of allowed directives (i.e. ``instance``) entries parsed by
    :meth:`_parse`.

    """
    factory: ImportConfigFactory = field()
    """The factory that created this prototype."""

    name: str = field()
    """The name of the instance to create, which is usually the application
    config section name.

    """
    config_str: str = field()
    """The string parsed from the parethesis in the prototype string."""

    @persisted('_parse_pw', allocation_track=False)
    def _parse(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        conf: str = self.config_str
        instance_params: Dict[str, Any] = {}
        inst_conf: Dict[str, Any] = None
        reload: bool = False
        try:
            if conf is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'parsing param config: {conf}')
                inst_conf = eval(conf)
                unknown: Set[str] = set(inst_conf.keys()) - \
                    self._CHILD_PARAM_DIRECTIVES
                if len(unknown) > 0:
                    raise FactoryError(f'Unknown directive(s): {unknown}',
                                       self.factory)
                if 'param' in inst_conf:
                    cparams = inst_conf['param']
                    cparams = self.factory.config.serializer.populate_state(
                        cparams, {})
                    instance_params.update(cparams)
                if 'reload' in inst_conf:
                    reload = inst_conf['reload']
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'setting reload: {reload}')
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'applying param config: {inst_conf}')
        finally:
            self.factory._set_reload(reload)
        return instance_params, inst_conf

    @property
    def params(self) -> Dict[str, Any]:
        return self._parse()[0]

    @property
    def config(self) -> Any:
        return self._parse()[1]


class ImportConfigFactory(ConfigFactory, Deallocatable):
    """Import a class by the fully qualified class name (includes the module).

    This is a convenience class for setting the parent class ``class_resolver``
    parameter.

    """
    _MODULES: ClassVar[Type[ImportConfigFactoryModule]] = []

    _MODULE_REGEXP: ClassVar[str] = r'(?:\((.+)\))?:\s*(.+)'
    """The ``instance`` regular expression used to identify children attributes
    to set on the object.  The process if creation can chain from parent to
    children recursively.

    """
    _INJECTS: ClassVar[Dict[str, str]] = {}
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

        :param kwargs: the key word arguments given to the super class

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
        self._init_modules()

    @classmethod
    def register_module(cls: Type, mod: ImportConfigFactoryModule):
        if cls not in cls._MODULES:
            cls._MODULES.append(mod)

    def _init_modules(self):
        modules: Tuple[ImportConfigFactoryModule] = tuple(
            map(lambda t: t(self), self._MODULES))
        mod_names: str = '|'.join(map(lambda m: m.name, modules))
        self._module_regexes: re.Pattern = re.compile(
            '^(' + mod_names + ')' + self._MODULE_REGEXP + '$', re.DOTALL)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'mod regex: {self._module_regexes}')
        self._modules: Dict[str, ImportConfigFactoryModule] = {
            m.name: m for m in modules}

    def __getstate__(self):
        state = dict(self.__dict__)
        state['_shared'] = None if self._shared is None else {}
        del state['class_resolver']
        del state['_modules']
        del state['_module_regexes']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.class_resolver = ImportClassResolver()
        self._init_modules()

    def clear(self):
        """Clear any shared instances.

        """
        if self._shared is not None:
            self._shared.clear()

    def clear_instance(self, name: str) -> Any:
        """Remove a shared (cached) object instance.

        :param name: the section name of the instance to evict and the same
                     string used to create with :meth:`instance` or
                     :meth:`new_instance`

        :return: the instance that was removed (if present), otherwise ``None``

        """
        if self._shared is not None:
            return self._shared.pop(name, None)

    def clone(self) -> Any:
        """Return a copy of this configuration factory that functionally works
        the same.  However, it does not copy over any resources generated during
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

    def instance(self, name: Optional[str] = None, *args, **kwargs):
        if self._shared is None:
            inst = super().instance(name, *args, **kwargs)
        else:
            inst = self._shared.get(name)
            if inst is None:
                inst = super().instance(name, *args, **kwargs)
                self._shared[name] = inst
        return inst

    def new_instance(self, name: str = None, *args, **kwargs):
        """Create a new instance without it being shared.  This is done by
        evicting the existing instance from the shared cache when it is created
        next time the contained instances are shared.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        :see: :meth:`instance`

        :see: :meth:`new_deep_instance`

        """
        inst = self.instance(name, *args, **kwargs)
        self.clear_instance(name)
        return inst

    def new_deep_instance(self, name: str = None, *args, **kwargs):
        """Like :meth:`new_instance` but copy all recursive instances as new
        objects as well.

        """
        prev_shared = self._shared
        self._shared = None
        try:
            inst = self.instance(name, *args, **kwargs)
        finally:
            self._shared = prev_shared
        return inst

    def _set_reload(self, reload: bool):
        self.reload = reload
        self.class_resolver.reload = reload

    def _attach_persistent(self, inst: Any, name: str, kwargs: Dict[str, str]):
        persist = persisted(**kwargs)
        new_meth = persist(lambda self: getattr(inst, name))
        new_meth = types.MethodType(new_meth, inst)
        setattr(inst, name, new_meth)

    def from_config_string(self, v: str) -> Any:
        """Create an instance from a string used as option values in the
        configuration.

        """
        m: re.Match = self._module_regexes.match(v)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'match: <{v}> -> {m}')
        if m is not None:
            name, config, section = m.groups()
            mod: ImportConfigFactoryModule = self._modules.get(name)
            if mod is not None:
                mod_inst = ModulePrototype(self, section, config)
                v = mod.instance(mod_inst)
        return v

    def _class_name_params(self, name: str) -> Tuple[str, Dict[str, Any]]:
        class_name: str
        params: Dict[str, Any]
        class_name, params = super()._class_name_params(name)
        insts = {}
        initial_reload = self.reload
        try:
            for k, v in params.items():
                if isinstance(v, str):
                    insts[k] = self.from_config_string(v)
        finally:
            self._set_reload(initial_reload)
        params.update(insts)
        return class_name, params

    def _instance(self, sec_name: str, cls: Type, *args, **kwargs):
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
            msg = ('Attempt redefine or reuse injection for class ' +
                   f'{class_name} in section {sec_name} previously ' +
                   f'defined in section {prev_defined_sec}')
            raise RedefinedInjectionError(msg, self)

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
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'base call instance: {sec_name}')
                inst = super()._instance(sec_name, cls, *args, **kwargs)
        finally:
            self._set_reload(initial_reload)

        self._add_injects(inst, pw_injects, reset_props)
        mod: ImportConfigFactoryModule
        for mod in self._modules.values():
            inst = mod.post_populate(inst)
        return inst

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
                    raise FactoryError(f"No property '{prop_name}' found '" +
                                       f"in section '{sec_name}'", self)
                params['initial_value'] = kwargs[prop_name]
                # don't delete the key here so that the type can be defined for
                # dataclasses, effectively as documentation
                #
                # del kwargs[prop_name]
                props.append((pw_name, prop_name, params))
        return props

    def _add_injects(self, inst: Any, pw_injects, reset_props: bool):
        cls: Type = inst.__class__
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


@dataclass
class ImportConfigFactoryModule(metaclass=ABCMeta):
    """A module used by :class:`.ImportConfigFactory` to create instances using
    special formatted string (i.e. ``instance:``).  Subclasses implement the
    object creation based on the formatting of the string.

    """
    _EMPTY_CHILD_PARAMS: ClassVar[Dict[str, Any]] = frozendict()
    """Constant used to create object instances with initializers that have no
    parameters.

    """
    factory: ImportConfigFactory = field()
    """The parent/owning configuration factory instance."""

    @abstractmethod
    def _instance(self, proto: ModulePrototype) -> Any:
        pass

    def post_populate(self, inst: Any) -> Any:
        """Called to populate or replace the created instance after being
        generated by :class:`.ImportConfigFactory`.

        """
        return inst

    @property
    def name(self) -> str:
        """The name of the module and prefix used in the instance formatted
        string.

        """
        return self._NAME

    def instance(self, proto: ModulePrototype) -> Any:
        """Return a new instance from the a prototype input."""
        return self._instance(proto)

    def _create_instance(self, section: str, config_params: Dict[str, str],
                         params: Dict[str, Any]) -> Any:
        """Create the instance using of an object using :obj:`factory`.

        :param section: the name of the section in the app config

        :param config_params: configuration based parameters to indicate (i.e.
                              whether to share the instance, create a deep copy
                              etc)

        :param params: the parameters given to the class initializer

        """
        fac: ImportConfigFactory = self.factory
        secs = fac.config.serializer.parse_object(section)
        if isinstance(secs, (tuple, list)):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'list instance: {type(secs)}')
            inst = list(map(lambda s: fac.instance(s, **params), secs))
            if isinstance(secs, tuple):
                inst = tuple(inst)
        elif isinstance(secs, dict):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'dict instance: {type(secs)}')
            inst = {}
            for k, v in secs.items():
                v = fac.instance(v, **params)
                inst[k] = v
        elif isinstance(secs, str):
            create_type: str = None
            try:
                if config_params is not None:
                    create_type: str = config_params.get('share')
                meth: Callable = {
                    None: fac.instance,
                    'default': fac.instance,
                    'evict': fac.new_instance,
                    'deep': fac.new_deep_instance,
                }.get(create_type)
                if meth is None:
                    raise FactoryError('Unknown create type: {create_type}')
                inst = meth(secs, **params)
            except Exception as e:
                raise FactoryError(
                    f"Could not create instance from section '{section}'",
                    fac) from e
        else:
            raise FactoryError(
                f'Unknown instance type {type(secs)}: {secs}', fac)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance in section {section} ' +
                         f'with {params}, config: {config_params}')
        return inst


@dataclass
class _InstanceImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that uses the :obj:`factory` to create the instance from a
    section.

    The configuration string prototype has the form::

        instance[(<parameters>)]: <instance section name>

    Parameters are option, but when included are used as parameters to the new
    instance's initializer.

    """
    _NAME: ClassVar[str] = 'instance'

    def _instance(self, proto: ModulePrototype) -> Any:
        return self._create_instance(proto.name, proto.config, proto.params)


ImportConfigFactory.register_module(_InstanceImportConfigFactoryModule)


@dataclass
class _AsDictImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that uses the :obj:`factory` to create the instance from a
    section as a :class:`builtins.dict` instead of :class:`.Settings`.

    The configuration string prototype has the form::

        asdict: <section name>

    """
    _NAME: ClassVar[str] = 'asdict'

    def _instance(self, proto: ModulePrototype) -> Any:
        obj = self._create_instance(proto.name, proto.config, proto.params)
        if not isinstance(obj, Settings):
            raise FactoryError(
                f'Expecting non-class (Settings) but got {type(obj)}')
        return obj.asdict()


ImportConfigFactory.register_module(_AsDictImportConfigFactoryModule)


@dataclass
class _AliasImportConfigFactoryModule(ImportConfigFactoryModule):
    """Like :class:`._InstanceImportConfigFactoryModule` but use the an alias
    for the instance section name.

    The configuration string prototype has the form::

        alias[(<parameters>)]: <section>:<option>

    The ``option`` in ``section`` is then used for the instance to be created by
    the factory.  The ``parameters`` are used to create the instance just like
    with :class:`._InstanceImportConfigFactoryModule`.

    This module is useful when using replaced values break the configuration
    loading order, or for sections/options not yet defined.  This can happen in
    CLI resource libraries application context definitions for default settings
    not yet loaded.

    """
    _NAME: ClassVar[str] = 'alias'
    _SECTION_OPTION: ClassVar[re.Pattern] = re.compile(r'^([^:]+):(.+)$')

    @classmethod
    def parse(cls: Type, s: str) -> Tuple[str, str]:
        m: re.Match = cls._SECTION_OPTION.match(s)
        if m is None:
            raise FactoryError(
                f"Expected format '<section>:<option>' but got: '{s}'")
        return m.groups()

    def _instance(self, proto: ModulePrototype) -> Any:
        sec: str
        option: str
        sec, option = self.parse(proto.name)
        config: Configurable = self.factory.config
        if sec not in config.sections:
            raise FactoryError(f"No such alias section: '{sec}'")
        alias: str = config.get_option(option, sec)
        return self._create_instance(alias, proto.config, proto.params)


ImportConfigFactory.register_module(_AliasImportConfigFactoryModule)


@dataclass
class _ObjectImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that creates an instance from a fully qualified class name.

    The configuration string prototype has the form::

        object[(<parameters>)]: <fully qualified class name>

    Parameters are option, but when included are used as parameters to the new
    instance's initializer.

    """
    _NAME: ClassVar[str] = 'object'

    def _instance(self, proto: ModulePrototype) -> Any:
        cls: Type = self.factory._find_class(proto.name)
        desc = f'object instance {proto.name}'
        return ConfigFactory._instance(
            self.factory, desc, cls, **proto.params)


ImportConfigFactory.register_module(_ObjectImportConfigFactoryModule)


@dataclass
class _DataClassImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that creates an instance of a dataclass using the class's
    metadata.

    The configuration string prototype has the form::

        dataclass(<fully qualified class name>): <instance section name>

    This is most useful in YAML for nested structure composite dataclass
    configurations.

    """
    _NAME: ClassVar[str] = 'dataclass'

    def _dataclass_from_dict(self, cls: Type, data: Any):
        if isinstance(data, str):
            data = self.factory.from_config_string(data)
            if isinstance(data, str):
                data = self.factory.config.serializer.parse_object(data)
        if dataclasses.is_dataclass(cls) and isinstance(data, dict):
            fieldtypes = {f.name: f.type for f in dataclasses.fields(cls)}
            try:
                param = {f: self._dataclass_from_dict(fieldtypes[f], data[f])
                         for f in data}
            except KeyError as e:
                raise FactoryError(
                    f"No datacalass field {e} in '{cls}, data: {data}'")
            data = cls(**param)
        elif isinstance(data, (tuple, list)):
            origin: Type = typing.get_origin(cls)
            cls: Type = typing.get_args(cls)
            if isinstance(cls, (tuple, list, set)) and len(cls) == 1:
                cls = next(iter(cls))
            data: Iterable[Any] = map(
                lambda x: self._dataclass_from_dict(cls, x), data)
            data = origin(data)
        return data

    def _instance(self, proto: ModulePrototype) -> Any:
        class_name: str = proto.config_str
        if not ClassImporter.is_valid_class_name(class_name):
            raise FactoryError(f'Not a valid class name: {class_name}')
        from_dict: Callable = self._dataclass_from_dict
        cls: Type = self.factory._find_class(class_name)
        ep: Dict[str, Any] = self._EMPTY_CHILD_PARAMS
        inst: Settings = self._create_instance(proto.name, ep, ep)
        if isinstance(inst, (tuple, list)):
            elems = map(lambda x: from_dict(cls, x.asdict()), inst)
            inst = inst.__class__(elems)
        else:
            inst = from_dict(cls, inst.asdict())
        return inst

    def post_populate(self, inst: Any) -> Any:
        if isinstance(inst, Settings) and len(inst) == 1:
            inst_dict = inst.asdict()
            k = next(iter(inst_dict.keys()))
            v = inst_dict[k]
            if isinstance(v, dict):
                cls: Optional[str] = v.pop(self._NAME, None)
                if cls is not None:
                    cls: Type = self.factory._find_class(cls)
                    dc: Any = self._dataclass_from_dict(cls, v)
                    inst_dict[k] = dc
        return inst


ImportConfigFactory.register_module(_DataClassImportConfigFactoryModule)


@dataclass
class _CallImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that calls a method of another instance in the application
    context.

    The configuration string prototype has the form::

        call[(<parameters>)]: <instance section name>


    Parameters may have a ``method`` key with the name of the method.  The
    remainder of the paraemters are used in the method call.

    """
    _NAME: ClassVar[str] = 'call'

    def _instance(self, proto: ModulePrototype) -> Any:
        cble: Any = self.factory.instance(proto.name)
        params: Dict[str, Any] = proto.params
        method_name: Optional[str] = params.pop('method', None)
        val: Any
        if method_name is None:
            # either the object is callable or an attribute
            attr_name: Optional[str] = params.pop('attribute', None)
            if attr_name is not None:
                # return the attribute if specified
                val = getattr(cble, attr_name)
            else:
                # otherwise assume it's callable and let it raise if not
                val = cble(**params)
        else:
            # call the specified method with parameters
            method: Any = getattr(cble, method_name)
            val = method(**params)
        return val


ImportConfigFactory.register_module(_CallImportConfigFactoryModule)
