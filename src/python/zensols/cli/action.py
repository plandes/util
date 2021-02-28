from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Dict, Tuple, Iterable, Set, List
from dataclasses import dataclass, field
import dataclasses
import logging
from zensols.persist import persisted
from zensols.introspect import (
    Class, ClassField, ClassParam, ClassMethod, ClassMethodArg,
    ClassInspector, ClassImporter,
)
from zensols.config import (
    Configurable, Dictable, ConfigFactory
)
from . import (
    ActionCliError, PositionalMetaData, OptionMetaData, ActionMetaData
)

logger = logging.getLogger(__name__)


class ActionCliManagerError(ActionCliError):
    """Raised by :class:`.ActionCliManager` for any problems creating
    :class:`.ActionCli` instances.

    """
    pass


class DocUtil(object):
    """A utility class to format API documentation parsed from the class.

    """
    @staticmethod
    def normalize(text: str) -> str:
        """Lower case and remove punctuation."""
        doc = text.lower()
        if doc[-1] == '.':
            doc = doc[0:-1]
        return doc


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
class ActionCli(Dictable):

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

    mnemonics: Dict[str, str] = field(default=None)
    """The name of the action given on the command line, which defaults to the name
    of the action.

    """

    option_includes: Set[str] = field(default=None)
    """A list of options to include, or all if ``None``."""

    option_excludes: Set[str] = field(default_factory=set)
    """A list of options to exclude, or none if ``None``."""

    first_pass: bool = field(default=False)
    """Whether or not this is a first pass action (i.e. such as setting the level
    in :class:`~zensols.cli.LogConfigurator`).

    """

    choices: Dict[str, List[str]] = field(default=None)
    """Map to a choices type."""

    def _is_option_enabled(self, name: str) -> bool:
        incs = self.option_includes
        excs = self.option_excludes
        enabled = ((incs is None) or (name in incs)) and (name not in excs)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'option {name} is enabled: {enabled}')
        return enabled

    def _add_option(self, name: str, omds: Set[OptionMetaData]):
        if self._is_option_enabled(name):
            opt: OptionMetaData = self.options[name]
            omds.add(opt)

    @property
    @persisted('_methods')
    def methods(self) -> Dict[str, ActionCliMethod]:
        meths: Dict[str, ActionCliMethod] = {}
        field_params: Set[OptionMetaData] = set()
        f: ClassField
        # add the dataclass fields that will populate the CLI as options
        for f in self.class_meta.fields.values():
            self._add_option(f.name, field_params)
        # create an action from each method
        for name in sorted(self.class_meta.methods.keys()):
            meth = self.class_meta.methods[name]
            meth_params = set(field_params)
            pos_args: List[PositionalMetaData] = []
            arg: ClassMethodArg
            for arg in meth.args:
                if arg.is_positional:
                    pos_args.append(PositionalMetaData(arg.name, arg.dtype))
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'adding option: {name}:{arg.name}')
                    self._add_option(arg.name, meth_params)
            # use what's given in the meta, or not present, the munged method
            # name as the mnemonic
            if self.mnemonics is not None:
                name = self.mnemonics.get(name)
                if name is None:
                    continue
            else:
                # no underscores in the CLI action names
                name = name.replace('_', '')
            if meth.doc is None:
                doc = self.class_meta.doc
            else:
                doc = meth.doc
            if doc is not None:
                doc = DocUtil.normalize(doc.text)
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
    @persisted('_meta_datas')
    def meta_datas(self) -> Tuple[ActionMetaData]:
        return tuple(map(lambda m: m.action_meta_data, self.methods.values()))


@dataclass
class ActionCliManager(Dictable):
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

    config_factory: ConfigFactory = field()
    """The configuration factory used to create :class:`.ActionCli` instances.

    """

    apps: Tuple[str] = field()
    """The application section names."""

    decorator_section_format: str = field(default='{section}_decorator')
    """Format of :class:`.ActionCli` configuration classes."""

    @property
    def config(self) -> Configurable:
        return self.config_factory.config

    def _create_short_name(self, long_name: str) -> str:
        """Auto generate  a single letter short option name.

        :param long_name: the name from which to pick a letter
        """
        for c in long_name:
            if c not in self._short_names:
                self._short_names.add(c)
                return c

    def _create_op_meta_data(self, pmeta: ClassParam,
                             meth: ClassMethod) -> OptionMetaData:
        """Creates an option meta data used in the CLI from a method parsed from the
        class's Python source code.

        """
        long_name = pmeta.name.replace('_', '')
        short_name = self._create_short_name(long_name)
        dtype = pmeta.dtype
        doc = pmeta.doc
        if doc is None:
            if (meth is not None) and (meth.doc is not None):
                doc = meth.doc.params.get(long_name)
        else:
            doc = doc.text
        if doc is not None:
            doc = DocUtil.normalize(doc)
        return OptionMetaData(
            long_name=long_name,
            short_name=short_name,
            dest=pmeta.name,
            dtype=dtype,
            default=pmeta.default,
            doc=doc)

    def _add_field(self, section: str, name: str, omd: OptionMetaData):
        """Adds the field by name that will later be used in a :class:`.ActionCli`.

        :raises ActionCliManagerError: if ``name`` has already been
                                       *registered*

        """
        prexist = self._fields.get(name)
        if prexist is not None and omd != prexist:
            raise ActionCliManagerError(
                f'duplicate field {name} -> {omd.long_name} in ' +
                f'{section} but not equal to {prexist}')
        self._fields[name] = omd

    def _add_action(self, action: ActionCli):
        """Adds add an action for each method parsed from the action cli Python source
        code.

        """
        if action.section in self._actions:
            raise ActionCliError(
                f'duplicate action for section: {action.section}')
        # for each dataclass field add that field 
        for name, fmd in action.class_meta.fields.items():
            omd = self._create_op_meta_data(fmd, None)
            self._add_field(action.section, fmd.name, omd)
        meth: ClassMethod
        # add a field for the arguments of each method
        for meth in action.class_meta.methods.values():
            arg: ClassMethodArg
            for arg in meth.args:
                omd = self._create_op_meta_data(arg, meth)
                # positional arguments are only referenced in the
                # ClassInspector parsed source code
                if not arg.is_positional:
                    self._add_field(action.section, arg.name, omd)
        self._actions[action.section] = action

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
        cls = ClassImporter(class_name).get_class()
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
        # if we found a decorator action cli config section, use it to set the
        # configuraiton of the CLI interacts
        if conf_sec in self.config.sections:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'found configuration section: {conf_sec}')
            action = self.config_factory.instance(conf_sec, **params)
        else:
            if hasattr(cls, self.CLASS_META_ATTRIBUTE):
                cmconf = getattr(cls, self.CLASS_META_ATTRIBUTE)
                params.update(cmconf)
            action = ActionCli(**params)
        logger.debug(f'created action: {action}')
        self._add_action(action)

    @property
    @persisted('_actions_pw')
    def actions(self) -> Dict[str, ActionCli]:
        """Get a list of action CLIs that is used in :class:`.CommandLineParser` to
        create instances of the application.  Each action CLI has a list of 

        :return: keys are the configuration sections with the action CLIs as
                 values

        """
        self._short_names: Set[str] = set()
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
