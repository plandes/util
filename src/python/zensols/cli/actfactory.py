from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Dict, Tuple, Iterable, Set
from dataclasses import dataclass, field
import dataclasses
import logging
from pathlib import Path
from itertools import chain
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


class ActionCliFactoryError(ActionCliError):
    pass


@dataclass
class ActionCliMetaData(Dictable):
    section: str = field()
    """The application section to introspect."""

    class_meta: DataClass = field()
    """The target class meta data parsed by :class:`.DataClassInspector`

    """

    options: Dict[str, OptionMetaData] = field(default=None)
    """Options added by :class:`.ActionCliFactory`, which are those options parsed
    by the entire class metadata.

    """

    def __post_init__(self):
        self.name = self.section.replace('_', '')


@dataclass
class ActionCli(Dictable):
    action_cli_meta_data: ActionCliMetaData
    mnemonic: str = field(default=None)
    option_includes: Tuple = field(default=None)
    #doc: str = field(default=None)
    first_pass: bool = field(default=False)

    @property
    def name(self) -> str:
        return self.action_cli_meta_data.name

    @property
    def meta_datas(self):
        acm = self.action_cli_meta_data
        omds: Tuple[OptionMetaData] = []
        f: DataClassField
        for f in acm.class_meta.fields.values():
            if (self.option_includes is None) or \
               (f.name in self.option_includes):
                omds.append(acm.options[f.name])
        meta_data = ActionMetaData(
            name=self.mnemonic or self.name,
            doc='NO DOC',
            options=omds,
            first_pass=self.first_pass)
        return [meta_data]


@dataclass
class ActionCliFactory(Dictable):
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

    def _create_option_meta_data(self, pmeta: DataClassParam) -> OptionMetaData:
        long_name = pmeta.name.replace('_', '')
        short_name = self._create_short_name(long_name)
        if pmeta.dtype == 'Path':
            dtype = Path
        elif pmeta.dtype is None:
            dtype = str
        elif pmeta.dtype in self.DATA_TYPE:
            dtype = eval(pmeta.dtype)
        else:
            raise ActionCliFactoryError(
                f'non-supported data type: {pmeta.dtype}')
        return OptionMetaData(
            long_name=long_name,
            short_name=short_name,
            dest=pmeta.name,
            dtype=dtype,
            default=pmeta.default,
            doc=pmeta.doc)

    def _add_field(self, section: str, name: str, omd: OptionMetaData):
        prexist = self._fields.get(name)
        if prexist is not None and omd != prexist:
            raise ActionCliFactoryError(
                f'duplicate field {name} -> {omd.long_name} in ' +
                f'{section} but not equal to {prexist}')
        self._fields[name] = omd

    def _add_action_meta(self, meta: ActionCliMetaData):
        if meta.name in self._meta_datas:
            raise ActionCliFactoryError(
                f'duplicate meta data: {meta.name}')
        for name, fmd in meta.class_meta.fields.items():
            omd = self._create_option_meta_data(fmd)
            self._add_field(meta.section, fmd.name, omd)
        meth: DataClassMethod
        for meth in meta.class_meta.methods.values():
            arg: DataClassMethodArg
            for arg in meth.args:
                print(arg)
                omd = self._create_option_meta_data(arg)
                self._add_field(meta.section, arg.name, omd)
        self._meta_datas[meta.name] = meta

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
        self._add_action_meta(ActionCliMetaData(section, meta))

    def _create_actions(self, acms: Tuple[ActionCliMetaData]):
        actions = {}
        for acm in acms:
            conf_sec = self.decorator_section_format.format(
                **{'section': acm.section})
            if conf_sec in self.config.sections:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'found configuration section: {conf_sec}')
                action = self.config_factory.instance(
                    conf_sec, action_cli_meta_data=acm)
            else:
                action = ActionCli(acm)
            actions[action.name] = action
        return actions

    @property
    @persisted('_actions')
    def actions(self) -> Dict[str, ActionCli]:
        self._short_names: Set[str] = set()
        self._fields: Dict[str, OptionMetaData] = {}
        self._meta_datas: Dict[str, ActionCliMetaData] = {}
        for app in self.apps:
            self._add_app(app)
        acms = tuple(self._meta_datas.values())
        for acm in acms:
            acm.options = self._fields
        actions = self._create_actions(acms)
        del self._short_names
        del self._fields
        return actions

    @property
    @persisted('_meta_datas')
    def action_meta_datas(self) -> Tuple[ActionMetaData]:
        return tuple(chain.from_iterable(
            map(lambda a: a.meta_datas, self.actions.values())))

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f), 'actions'.split())

    def tmp(self):
        #self.actions
        self.write()
