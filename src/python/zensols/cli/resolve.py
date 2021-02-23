from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Dict, Tuple, Iterable, Set
from dataclasses import dataclass, field
import dataclasses
import logging
from pathlib import Path
from zensols.util import (
    DataClassInspector, DataClassMetaData, FieldMetaData
)
from zensols.config import (
    Configurable, Dictable, ConfigFactory, ClassImporter
)
from . import ActionCliError, OptionMetaData, ActionMetaData

logger = logging.getLogger(__name__)


class ActionCliResolverError(ActionCliError):
    pass


@dataclass
class ActionCliMetaData(Dictable):
    section: str = field()
    """The application section to introspect."""

    class_meta: DataClassMetaData

    options: Dict[str, OptionMetaData] = field(default=None)

    def __post_init__(self):
        self.name = self.section.replace('_', '')


@dataclass
class ActionCli(Dictable):
    action_cli_meta_data: ActionCliMetaData

    def __post_init__(self):
        acm = self.action_cli_meta_data
        f: FieldMetaData
        omds: Tuple[OptionMetaData] = []
        for f in acm.class_meta.fields.values():
            omds.append(acm.options[f.name])
        doc = acm.class_meta.cls.__doc__
        if doc is not None:
            doc = doc.strip()
            if len(doc) == 0:
                doc = None
        self.meta_data = ActionMetaData(
            name=acm.name,
            doc=doc,
            options=omds)
        self.name = self.meta_data.name


@dataclass
class ActionCliResolver(Dictable):
    SECTION = 'cli'
    """The application context section."""

    DATA_TYPE_STRS = set(map(lambda t: t.__name__, OptionMetaData.DATA_TYPES))

    config_factory: ConfigFactory
    apps: Tuple[str]

    @property
    def config(self) -> Configurable:
        return self.config_factory.config

    def _create_short_name(self, long_name: str) -> str:
        for c in long_name:
            if c not in self._short_names:
                self._short_names.add(c)
                return c

    def _create_option_meta_data(self, fmd: FieldMetaData) -> OptionMetaData:
        long_name = fmd.name.replace('_', '')
        short_name = self._create_short_name(long_name)
        default = None
        if fmd.dtype == 'Path':
            dtype = Path
        elif fmd.dtype in self.DATA_TYPE_STRS:
            dtype = eval(fmd.dtype)
        else:
            raise ActionCliResolverError(
                f'non-supported data type: {fmd.dtype}')
        if fmd.kwargs is not None:
            default = fmd.kwargs.get('default')
        return OptionMetaData(
            long_name=long_name,
            short_name=short_name,
            dest=fmd.name,
            dtype=dtype,
            default=default,
            doc=fmd.doc)

    def _add_action_meta(self, meta: ActionCliMetaData):
        if meta.name in self._meta_datas:
            raise ActionCliResolverError(
                f'duplicate meta data: {meta.name}')
        for name, fmd in meta.class_meta.fields.items():
            omd = self._create_option_meta_data(fmd)
            prexist = self._fields.get(fmd.name)
            if prexist is not None and omd != prexist:
                raise ActionCliResolverError(
                    f'duplicate field {name} -> {omd.long_name} in ' +
                    f'{meta.section} but not equal to {prexist}')
            self._fields[fmd.name] = omd
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
        meta: DataClassMetaData = dh.get_meta_data()
        self._add_action_meta(ActionCliMetaData(section, meta))

    @property
    def actions(self) -> Dict[str, ActionCli]:
        self._short_names: Set[str] = set()
        self._fields: Dict[str, OptionMetaData] = {}
        self._meta_datas: Dict[str, ActionCliMetaData] = {}
        for app in self.apps:
            self._add_app(app)
        acms = tuple(self._meta_datas.values())
        for acm in acms:
            acm.options = self._fields
        actions = {a.name: a for a in map(ActionCli, acms)}
        del self._short_names
        del self._fields
        return actions

    @property
    def action_meta_datas(self) -> Tuple[ActionMetaData]:
        return tuple(map(lambda a: a.meta_data, self.actions.values()))

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f), 'actions'.split())

    def tmp(self):
        #self.actions
        self.write()
