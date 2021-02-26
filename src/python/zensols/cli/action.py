from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Dict, Tuple, Iterable, Set, List
from dataclasses import dataclass, field
import dataclasses
import logging
from pathlib import Path
from zensols.persist import persisted
from zensols.util import (
    DataClassInspector, DataClass,
    DataClassField, DataClassParam, DataClassMethod, DataClassMethodArg
)
from zensols.config import (
    Configurable, Dictable, ConfigFactory, ClassImporter
)
from . import ActionCliError, OptionMetaData, ActionMetaData

logger = logging.getLogger(__name__)


class ActionCliManagerError(ActionCliError):
    """Raised by :class:`.ActionCliManager` for any problems creating
    :class:`.ActionCli` instances.

    """
    pass


@dataclass
class ActionCli(Dictable):
    """A command that is invokeable on the command line.

    """
    section: str = field()
    """The application section to introspect."""

    class_meta: DataClass = field()
    """The target class meta data parsed by :class:`.DataClassInspector`

    """

    options: Dict[str, OptionMetaData] = field(default=None)
    """Options added by :class:`.ActionCliManager`, which are those options parsed
    by the entire class metadata.

    """

    mnemonics: Dict[str, str] = field(default_factory=dict)
    """The name of the action given on the command line, which defaults to the name
    of the action.

    """

    option_includes: Set[str] = field(default=None)
    """A list of options to include, or all if ``None``."""

    option_excludes: Set[str] = field(default_factory=set)
    """A list of options to exclude, or none if ``None``."""

    first_pass: bool = field(default=False)
    """Whether or not this is a first pass action (i.e. such as setting the level
    in :class:`~zensols.cli.LogConfigurator`

    """

    @property
    @persisted('_meta_datas')
    def meta_datas(self) -> Tuple[ActionMetaData]:
        metas: List[ActionMetaData] = []
        omds: Set[OptionMetaData] = set()
        f: DataClassField
        incs = self.option_includes
        excs = self.option_excludes
        for f in self.class_meta.fields.values():
            if ((incs is None) or (f.name in incs)) and (f.name not in excs):
                omds.add(self.options[f.name])
        for name in sorted(self.class_meta.methods.keys()):
            meth = self.class_meta.methods[name]
            arg: DataClassMethodArg
            for arg in meth.args:
                if arg.is_positional:
                    pass
                else:
                    arg_omd: OptionMetaData = self.options[arg.name]
                    omds.add(arg_omd)
            if meth.doc is None:
                doc = self.class_meta.doc
            else:
                doc = meth.doc
            if doc is not None:
                doc = doc.text
            if name in self.mnemonics:
                name = self.mnemonics[name]
            meta = ActionMetaData(
                name=name,
                doc=doc,
                options=sorted(omds),
                first_pass=self.first_pass)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'adding metadata: {meta}')
            metas.append(meta)
        return metas


@dataclass
class ActionCliManager(Dictable):
    SECTION = 'cli'
    """The application context section."""

    DATA_TYPE = set(map(lambda t: t.__name__, OptionMetaData.DATA_TYPES))
    """Supported data types mapped from data class fields."""

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
        for c in long_name:
            if c not in self._short_names:
                self._short_names.add(c)
                return c

    def _create_op_meta_data(self, pmeta: DataClassParam,
                             meth: DataClassMethod) -> OptionMetaData:
        long_name = pmeta.name.replace('_', '')
        short_name = self._create_short_name(long_name)
        if pmeta.dtype == 'Path':
            dtype = Path
        elif pmeta.dtype is None:
            dtype = str
        elif pmeta.dtype in self.DATA_TYPE:
            dtype = eval(pmeta.dtype)
        else:
            raise ActionCliManagerError(
                f'non-supported data type: {pmeta.dtype}')
        doc = pmeta.doc
        if doc is None:
            if (meth is not None) and (meth.doc is not None):
                doc = meth.doc.params.get(long_name)
        else:
            doc = doc.text
        return OptionMetaData(
            long_name=long_name,
            short_name=short_name,
            dest=pmeta.name,
            dtype=dtype,
            default=str(pmeta.default),
            doc=doc)

    def _add_field(self, section: str, name: str, omd: OptionMetaData):
        prexist = self._fields.get(name)
        if prexist is not None and omd != prexist:
            raise ActionCliManagerError(
                f'duplicate field {name} -> {omd.long_name} in ' +
                f'{section} but not equal to {prexist}')
        self._fields[name] = omd

    def _add_action(self, action: ActionCli):
        for name, fmd in action.class_meta.fields.items():
            omd = self._create_op_meta_data(fmd, None)
            self._add_field(action.section, fmd.name, omd)
        meth: DataClassMethod
        for meth in action.class_meta.methods.values():
            print('M', meth)
            arg: DataClassMethodArg
            for arg in meth.args:
                omd = self._create_op_meta_data(arg, meth)
                self._add_field(action.section, arg.name, omd)
        self._actions[action.section] = action

    def _add_app(self, section: str):
        config = self.config
        class_name: str = config.get_option('class_name', section)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'building CLI on class: {class_name}')
        cls = ClassImporter(class_name).get_class()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'resolved to class: {cls}')
        if not dataclasses.is_dataclass(cls):
            raise ActionCliError('application CLI app must be a dataclass')
        dh = DataClassInspector(cls)
        meta: DataClass = dh.get_meta_data()
        params = {'section': section,
                  'class_meta': meta,
                  'options': self._fields}
        conf_sec = self.decorator_section_format.format(**{'section': section})
        if conf_sec in self.config.sections:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'found configuration section: {conf_sec}')
            action = self.config_factory.instance(conf_sec, **params)
        else:
            action = ActionCli(**params)
        logger.debug(f'created action: {action}')
        self._add_action(action)

    @property
    @persisted('_actions_pw')
    def actions(self) -> Dict[str, ActionCli]:
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

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f), 'actions'.split())

    def tmp(self):
        #self.actions
        self.write()
