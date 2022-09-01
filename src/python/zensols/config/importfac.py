"""A configuration factory that (re)imports based on class name.

"""
__author__ = 'Paul Landes'

import typing
from typing import Tuple, Dict, Optional, Union, Any, Type, Iterable
import dataclasses
import logging
import types
import re
from frozendict import frozendict
from zensols.introspect import ClassResolver
from zensols.persist import persisted, PersistedWork, Deallocatable
from . import Settings, FactoryError, ImportClassResolver, ConfigFactory

logger = logging.getLogger(__name__)


class RedefinedInjectionError(FactoryError):
    """Raised when any attempt to redefine or reuse injections for a class.

    """
    pass


class ImportConfigFactory(ConfigFactory, Deallocatable):
    """Import a class by the fully qualified class name (includes the module).

    This is a convenience class for setting the parent class ``class_resolver``
    parameter.

    """
    DATACLASS = 'dataclass'
    """Similar to :obj:`~zensols.config.facbase.ConfigFactory.CLASS_NAME`, an
    attribute in a section that allows for creating instances of dataclasses
    inline (i.e in YAML).

    """
    _INSTANCE_REGEXP = re.compile(r'^instance(?:\((.+)\))?:\s*(.+)$',
                                  re.DOTALL)
    """The ``instance`` regular expression used to identify children attributes to
    set on the object.  The process if creation can chain from parent to
    children recursively.

    """
    _OBJECT_REGEXP = re.compile(r'^object(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    """The ``object`` regular expression used to instantiate non-shared singleton
    instances tied to the outside instance..

    """
    _DATACLASS_REGEXP = re.compile(r'^dataclass\((.+)\):\s*(.+)$', re.DOTALL)
    """The ``dataclass`` regular expression used to create Python dataclasses with
    nested data in formats such as YAML.

    """
    _INJECTS = {}
    """Track injections to fail on any attempts to redefine."""

    _EMPTY_CHILD_PARAMS = frozendict()

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
        """Create a new instance without it being shared.  This is done by purging the
        existing instance from the shared cache when it is created next time
        the contained instances are shared.

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
        """Like :meth:`new_instance` but copy all recursive instances as new objects as
        well.

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
            try:
                inst = self.instance(secs, **params)
            except Exception as e:
                raise FactoryError(
                    f"Could not create instance from section '{section}'",
                    self) from e
        else:
            raise FactoryError(
                f'Unknown instance type {type(secs)}: {secs}', self)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance in section {section} ' +
                         f'with {params}, config: {config_params}')
        return inst

    def _parse_child_params(self, pconfig: str) -> Tuple[Dict[str, str], bool]:
        child_params = {}
        inst_conf = None
        reload = False
        defined_directives = set('param reload type'.split())
        if pconfig is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'parsing param config: {pconfig}')
            inst_conf = eval(pconfig)
            unknown = set(inst_conf.keys()) - defined_directives
            if len(unknown) > 0:
                raise FactoryError(f'Unknown directive(s): {unknown}', self)
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
        return child_params, inst_conf

    def _populate_instances(self, pconfig: str, section: str):
        child_params, inst_conf = self._parse_child_params(pconfig)
        return self._create_instance(section, inst_conf, child_params)

    def _object_instance(self, pconfig: str, class_name: str):
        params, inst_conf = self._parse_child_params(pconfig)
        cls: Type = self._find_class(class_name)
        desc = f'object instance {class_name}'
        return super()._instance(desc, cls, **params)

    def _dataclass_from_dict(self, cls: Type, data: Any):
        if isinstance(data, str):
            data = self.from_config_string(data)
            if isinstance(data, str):
                data = self.config.serializer.parse_object(data)
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

    def _dataclass_instance(self, class_name: str, section: str):
        from_dict = self._dataclass_from_dict
        cls: Type = self._find_class(class_name)
        params = self._EMPTY_CHILD_PARAMS
        inst: Settings = self._create_instance(section, params, params)
        if isinstance(inst, (tuple, list)):
            elems = map(lambda x: from_dict(cls, x.asdict()), inst)
            inst = inst.__class__(elems)
        else:
            inst = from_dict(cls, inst.asdict())
        return inst

    def from_config_string(self, v: str) -> Any:
        """Create an instance from a string that looks like :obj:`_INSTANCE_REGEXP` or
        :obj:`_OBJECT_REGEXP` used as option values in the configuration.

        """
        m = self._INSTANCE_REGEXP.match(v)
        if m is not None:
            pconfig, section = m.groups()
            v = self._populate_instances(pconfig, section)
        else:
            m = self._OBJECT_REGEXP.match(v)
            if m is not None:
                pconfig, class_name = m.groups()
                v = self._object_instance(pconfig, class_name)
            else:
                m = self._DATACLASS_REGEXP.match(v)
                if m is not None:
                    class_name, section = m.groups()
                    v = self._dataclass_instance(class_name, section)
        return v

    def _class_name_params(self, name):
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
            msg = ('attempt redefine or reuse injection for class ' +
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
        if isinstance(inst, Settings) and len(inst) == 1:
            self._populate_dataclass(inst)
        return inst

    def _populate_dataclass(self, inst: Any):
        inst_dict = inst.asdict()
        k = next(iter(inst_dict.keys()))
        v = inst_dict[k]
        if isinstance(v, dict):
            cls: Optional[str] = v.pop(self.DATACLASS, None)
            if cls is not None:
                cls: Type = self._find_class(cls)
                dc: Any = self._dataclass_from_dict(cls, v)
                inst_dict[k] = dc

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
