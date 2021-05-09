from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Dict, Tuple, Iterable, Set, List, Any
from dataclasses import dataclass, field
import dataclasses
import logging
import copy as cp
from itertools import chain
from zensols.persist import persisted, PersistableContainer
from zensols.introspect import (
    Class, ClassField, ClassParam, ClassMethod, ClassMethodArg,
    ClassInspector, ClassImporter,
)
from zensols.config import (
    Configurable, Dictable, ConfigFactory
)
from . import (
    DocUtil, ActionCliError, PositionalMetaData, OptionMetaData, ActionMetaData
)

logger = logging.getLogger(__name__)


class ActionCliManagerError(ActionCliError):
    """Raised by :class:`.ActionCliManager` for any problems creating
    :class:`.ActionCli` instances.

    """
    pass


@dataclass
class ActionCliMethod(Dictable):
    """A "married" action meta data / class method pair.  This is a pair of action
    meta data that describes how to interpret it as a CLI action and the Python
    class meta data method, which is used later to invoke the action (really
    command).

    """
    action_meta_data: ActionMetaData = field()
    """The action meta data for ``method``."""

    method: ClassMethod = field(repr=False)
    """The method containing information about the source class method to invoke
    later.

    """


@dataclass
class ActionCli(PersistableContainer, Dictable):
    """A set of commands that is invokeable on the command line, one for each
    registered method of a class (usually a :class:`dataclasses.dataclass`.
    This contains meta data necesary to create a full usage command line
    documentation and parse the user's input.

    """
    section: str = field()
    """The application section to introspect."""

    class_meta: Class = field(repr=False)
    """The target class meta data parsed by :class:`.ClassInspector`

    """

    options: Dict[str, OptionMetaData] = field(default=None)
    """Options added by :class:`.ActionCliManager`, which are those options parsed
    by the entire class metadata.

    """

    mnemonic_includes: Set[str] = field(default=None)
    """A list of mnemonicss to include, or all if ``None``."""

    mnemonic_excludes: Set[str] = field(default_factory=set)
    """A list of mnemonicss to exclude, or none if ``None``."""

    mnemonic_overrides: Dict[str, str] = field(default=None)
    """The name of the action given on the command line, which defaults to the name
    of the action.

    """

    option_includes: Set[str] = field(default=None)
    """A list of options to include, or all if ``None``."""

    option_excludes: Set[str] = field(default_factory=set)
    """A list of options to exclude, or none if ``None``."""

    option_overrides: Dict[str, Dict[str, str]] = field(default=None)
    """Overrides when creating new :class:`.OptionMetaData` where the keys are the
    option names (field or method parameter) and the values are the dict that
    clobbers respective keys.

    :see: :meth:`.ActionCliManager._create_op_meta_data`

    """

    first_pass: bool = field(default=False)
    """Whether or not this is a first pass action (i.e. such as setting the level
    in :class:`~zensols.cli.LogConfigurator`).

    """

    always_invoke: bool = field(default=False)
    """If ``True``, always invoke all methods for the action regardless if an
    action mnemonic and options pertaining to the action are not given by the
    user/command line.  This is useful for configuration first pass type
    classes like :class:`.PackageInfoImporter` to force the CLI API to invoke
    it, as otherwise there's no indication to the CLI that it needs to be
    called.

    """

    def _is_option_enabled(self, name: str) -> bool:
        """Return ``True`` if the option is enabled and eligible to be added to the
        command line.

        """
        incs = self.option_includes
        excs = self.option_excludes
        enabled = ((incs is None) or (name in incs)) and (name not in excs)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'option {name} is enabled: {enabled}')
        return enabled

    def _is_mnemonic_enabled(self, name: str) -> bool:
        """Return ``True`` if the action for the mnemonic is enabled and eligible to be
        added to the command line.

        """
        incs = self.mnemonic_includes
        excs = self.mnemonic_excludes
        enabled = ((incs is None) or (name in incs)) and (name not in excs)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'mnemonic {self.section}:{name} is enabled: {enabled} for ' +
                         f'{self.class_meta.name}: [inc={incs},exc={excs}]')
        return enabled

    def _add_option(self, name: str, omds: Set[OptionMetaData]):
        """Add an :class:`.OptionMetaData` from the previously collected options.

        :param name: the name of the option

        :param omds: the set to populate from :obj:`options`

        """
        if self._is_option_enabled(name):
            opt: OptionMetaData = self.options[name]
            omds.add(opt)

    def _normalize_name(self, s: str) -> str:
        """Normalize text of mneomincs and positional arguments."""
        return s.replace('_', '')

    @property
    @persisted('_methods')
    def methods(self) -> Dict[str, ActionCliMethod]:
        """Return the methods for this action CLI with method name keys.

        """
        meths: Dict[str, ActionCliMethod] = {}
        field_params: Set[OptionMetaData] = set()
        f: ClassField
        # add the dataclass fields that will populate the CLI as options
        for f in self.class_meta.fields.values():
            self._add_option(f.name, field_params)
        # create an action from each method
        for name in sorted(self.class_meta.methods.keys()):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'creating method {name}')
            meth: ClassMethod = self.class_meta.methods[name]
            meth_params: Set[OptionMetaData] = set(field_params)
            pos_args: List[PositionalMetaData] = []
            arg: ClassMethodArg
            # add positionl arguments from the class meta data
            for arg in meth.args:
                if arg.is_positional:
                    opt: Dict[str, str] = None
                    if self.option_overrides is not None:
                        opt = self.option_overrides.get(arg.name)
                    # first try to get it from any mapping from the long name
                    if opt is not None and 'long_name' in opt:
                        pname = opt['long_name']
                    else:
                        # use the argument name in the method but normalize it
                        # to make it appear in CLI parlance
                        pname = self._normalize_name(arg.name)
                    pos_args.append(PositionalMetaData(pname, arg.dtype))
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'adding option: {name}:{arg.name}')
                    self._add_option(arg.name, meth_params)
            # skip disabled mnemonics (using mnemonic_includes)
            if not self._is_mnemonic_enabled(name):
                continue
            # customize mnemonic/action data if given (either string names, or
            # dictionaries with more information)
            if self.mnemonic_overrides is not None and \
               name in self.mnemonic_overrides:
                override: Any = self.mnemonic_overrides[name]
                if isinstance(override, str):
                    name = override
                elif isinstance(override, dict):
                    o_name: str = override.get('name')
                    option_includes: Set[str] = override.get('option_includes')
                    option_excludes: Set[str] = override.get('option_excludes')
                    if o_name is not None:
                        name = o_name
                    if option_includes is not None:
                        meth_params: Set[OptionMetaData] = set(
                            filter(lambda o: o.long_name in option_includes,
                                   meth_params))
                    if option_excludes is not None:
                        meth_params: Set[OptionMetaData] = set(
                            filter(lambda o: o.long_name not in option_excludes,
                                   meth_params))
                else:
                    raise ActionCliManagerError(
                        f'unknown override: {override} ({type(override)})')
            else:
                # no underscores in the CLI action names
                name = self._normalize_name(name)
            # get the action help from the method if available, then class
            if meth.doc is None:
                doc = self.class_meta.doc
            else:
                doc = meth.doc
            if doc is not None:
                doc = DocUtil.normalize(doc.text)
            # add the meta data
            meta = ActionMetaData(
                name=name,
                doc=doc,
                options=tuple(sorted(meth_params)),
                positional=tuple(pos_args),
                first_pass=self.first_pass)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'adding metadata: {meta}')
            meths[name] = ActionCliMethod(meta, meth)
        self.options = None
        return meths

    @property
    @persisted('_meta_datas', deallocate_recursive=True)
    def meta_datas(self) -> Tuple[ActionMetaData]:
        """Return action meta data across all methods.

        """
        return tuple(map(lambda m: m.action_meta_data, self.methods.values()))



@dataclass
class ActionCliManager(PersistableContainer, Dictable):
    """An :class:`.ActionCli` is created from the configuration given by the
    section.  Optionally, another section using :obj:`decorator_section_format`
    will be read to add additional metadata and configuration to instantiated
    object.  The decorated information is used to help bridge between the class
    given to be instantiated and the CLI.

    :see: :obj:`actions`

    :see: :obj:`actions_by_meta_data_name`

    """
    SECTION = 'cli'
    """The application context section."""

    CLASS_META_ATTRIBUTE = 'CLI_META'
    """The class level attribute on application classes containing a stand in
    (otherwise missing section configuration :class:`.ActionCli`.

    """

    _CLASS_IMPORTERS = {}
    """Resolved class cache (see :meth:`_resolve_class`).

    """

    config_factory: ConfigFactory = field()
    """The configuration factory used to create :class:`.ActionCli` instances.

    """

    apps: Tuple[str] = field()
    """The application section names."""

    cleanups: Tuple[str] = field(default=None)
    """The sections to remove after the application is built."""

    decorator_section_format: str = field(default='{section}_decorator')
    """Format of :class:`.ActionCli` configuration classes."""

    doc: str = field(default=None)
    """The application documentation."""

    default_action: str = field(default=None)
    """The default mnemonic use when the user does not supply one."""

    @property
    def config(self) -> Configurable:
        return self.config_factory.config

    def _create_short_name(self, long_name: str) -> str:
        """Auto generate  a single letter short option name.

        :param long_name: the name from which to pick a letter
        """
        for c in long_name:
            if c not in self._short_names:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'adding short name for {long_name}: {c}')
                self._short_names.add(c)
                return c

    def _create_op_meta_data(self, pmeta: ClassParam, meth: ClassMethod,
                             action_cli: ActionCli) -> OptionMetaData:
        """Creates an option meta data used in the CLI from a method parsed from the
        class's Python source code.

        """
        meta = None
        if action_cli._is_option_enabled(pmeta.name):
            long_name = pmeta.name.replace('_', '')
            short_name = self._create_short_name(long_name)
            dest = pmeta.name
            dtype = pmeta.dtype
            doc = pmeta.doc
            if doc is None:
                if (meth is not None) and (meth.doc is not None):
                    doc = meth.doc.params.get(long_name)
            else:
                doc = doc.text
            if doc is not None:
                doc = DocUtil.normalize(doc)
            params = {
                'long_name': long_name,
                'short_name': short_name,
                'dest': dest,
                'dtype': dtype,
                'default': pmeta.default,
                'doc': doc
            }
            if action_cli.option_overrides is not None:
                overrides = action_cli.option_overrides.get(pmeta.name)
                if overrides is not None:
                    params.update(overrides)
            meta = OptionMetaData(**params)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'created option meta: {meta}')
        return meta

    def _add_field(self, section: str, name: str, omd: OptionMetaData):
        """Adds the field by name that will later be used in a :class:`.ActionCli`.

        :raises ActionCliManagerError: if ``name`` has already been
                                       *registered*

        """
        prexist = self._fields.get(name)
        if prexist is not None:
            # we have to skip the short option compare since
            # ``_create_op_meta_data`` reassigns a new letter for all created
            # options
            prexist = cp.deepcopy(prexist)
            prexist.short_name = omd.short_name
            if omd != prexist:
                raise ActionCliManagerError(
                    f'duplicate field {name} -> {omd} in ' +
                    f'{section} but not equal to {prexist}')
        self._fields[name] = omd

    def _add_action(self, action: ActionCli):
        """Adds add an action for each method parsed from the action cli Python source
        code.

        """
        if action.section in self._actions:
            raise ActionCliError(
                f'duplicate action for section: {action.section}')
        # for each dataclass field used to create OptionMetaData's
        for name, fmd in action.class_meta.fields.items():
            omd = self._create_op_meta_data(fmd, None, action)
            if omd is not None:
                self._add_field(action.section, fmd.name, omd)
        meth: ClassMethod
        # add a field for the arguments of each method
        for meth in action.class_meta.methods.values():
            arg: ClassMethodArg
            for arg in meth.args:
                # positional arguments are only referenced in the
                # ClassInspector parsed source code
                if not arg.is_positional:
                    omd = self._create_op_meta_data(arg, meth, action)
                    if omd is not None:
                        self._add_field(action.section, arg.name, omd)
        self._actions[action.section] = action

    def _resolve_class(self, class_name: str) -> type:
        """Resolve a class using the caching those already dynamically resolved.

        """
        cls_imp: ClassImporter = self._CLASS_IMPORTERS.get(class_name)
        if cls_imp is None:
            # resolve the string fully qualified class name to a Python class
            # type
            cls_imp = ClassImporter(class_name, reload=False)
            cls = cls_imp.get_class()
            self._CLASS_IMPORTERS[class_name] = cls_imp
        else:
            cls = cls_imp.get_class()
        return cls

    def _add_app(self, section: str):
        """Add an :class:`.ActionCli` instanced from the configuration given by a
        section.  The application is added to :obj:`._actions`.  The section is
        parsed and use to instantiate an object using
        :class:`~zensols.config.factory.ImportConfigFactory`.

        Optionally, another section using :obj:`decorator_section_format` will
        be read to add additional metadata and configuration to instantiated
        object.  See the class docs.

        :param section: indicates which section to use with config factory

        """
        config = self.config
        class_name: str = config.get_option('class_name', section)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'building CLI on class: {class_name}')
        # resolve the string fully qualified class name to a Python class type
        cls = self._resolve_class(class_name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'resolved to class: {cls}')
        if not dataclasses.is_dataclass(cls):
            raise ActionCliError('application CLI app must be a dataclass')
        # parse the source Python code for the class
        inspector = ClassInspector(cls)
        meta: Class = inspector.get_class()
        # parameters to create the application with the config factory
        params = {'section': section,
                  'class_meta': meta,
                  'options': self._fields}
        conf_sec = self.decorator_section_format.format(**{'section': section})
        # start with class level meta data, allowing it to be overriden at the
        # application configuration level; note: tested with
        # `mnemonic_includes`, which appears to merge dictionaries, which is
        # probably the new 3.9 dictionary set union operations working by
        # default
        if hasattr(cls, self.CLASS_META_ATTRIBUTE):
            cmconf = getattr(cls, self.CLASS_META_ATTRIBUTE)
            params.update(cmconf)
        # if we found a decorator action cli config section, use it to set the
        # configuraiton of the CLI interacts
        if conf_sec in self.config.sections:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'found configuration section: {conf_sec}')
            action = self.config_factory.instance(conf_sec, **params)
            if not isinstance(action, ActionCli):
                raise ActionCliManagerError(
                    f'section instance {conf_sec} is not a class of ' +
                    f'type ActionCli, but {type(action)}')
        else:
            # use a default with parameters collected
            action = ActionCli(**params)
        logger.debug(f'created action: {action}')
        self._add_action(action)

    @property
    @persisted('_actions_pw')
    def actions(self) -> Dict[str, ActionCli]:
        """Get a list of action CLIs that is used in :class:`.CommandLineParser` to
        create instances of the application.  Each action CLI has a collection
        of :class:`.ActionMetaData` instances.

        :return: keys are the configuration sections with the action CLIs as
                 values

        """
        self._short_names: Set[str] = {'h', 'v'}
        self._fields: Dict[str, OptionMetaData] = {}
        self._actions: Dict[str, ActionCli] = {}
        try:
            for app in self.apps:
                self._add_app(app)
            actions = self._actions
        finally:
            del self._actions
            del self._short_names
            del self._fields
        return actions

    @property
    @persisted('_actions_ordered', deallocate_recursive=True)
    def actions_ordered(self) -> Tuple[ActionCli]:
        """Return all actions in the order they were given in the configuration.

        """
        acts = self.actions
        fp = filter(lambda a: a.first_pass, acts.values())
        sp = filter(lambda a: not a.first_pass, acts.values())
        return tuple(chain.from_iterable([fp, sp]))

    @property
    @persisted('_actions_by_meta_data_name_pw')
    def actions_by_meta_data_name(self) -> Dict[str, ActionCli]:
        """Return a dict of :class:`.ActionMetaData` instances, each of which is each
        mnemonic by name and the meta data by values.

        """
        actions = {}
        action: ActionCli
        for action in self.actions.values():
            meta: Tuple[ActionMetaData]
            for meta in action.meta_datas:
                if meta.name in actions:
                    raise ActionCliError(f'duplicate meta data: {meta.name}')
                actions[meta.name] = action
        return actions

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f), 'actions'.split())
