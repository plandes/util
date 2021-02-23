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
    section: str
    class_meta: DataClassMetaData

    def __post_init__(self):
        self.name = self.section.replace('_', '')


@dataclass
class ActionCliResolver(Dictable):
    SECTION = 'cli'
    """The application context section."""

    DATA_TYPE_STRS = set(map(lambda t: t.__name__, OptionMetaData.DATA_TYPES))

    config_factory: ConfigFactory
    apps: Tuple[str]
    meta_datas: Dict[str, ActionCliMetaData] = field(default_factory=dict)

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
        if meta.name in self.meta_datas:
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
        self.meta_datas[meta.name] = meta

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
        fdocs: Dict[str, FieldMetaData] = dh.get_field_docs()
        self._add_action_meta(ActionCliMetaData(section, fdocs))

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f), 'actions'.split())

    def _create_actions(self) -> Dict[str, ActionMetaData]:
        acts: Dict[str, ActionMetaData] = {}
        acm: ActionCliMetaData
        for acm in self.meta_datas.values():
            omds: Tuple[OptionMetaData] = tuple(
                map(lambda f: self._fields[f.name],
                    acm.class_meta.fields.values()))
            doc = acm.class_meta.cls.__doc__
            if doc is not None:
                doc = doc.strip()
                if len(doc) == 0:
                    doc = None
            am = ActionMetaData(
                name=acm.name,
                doc=doc,
                options=omds)
            acts[am.name] = am
        return acts

    @property
    def actions(self) -> Dict[str, ActionMetaData]:
        self._short_names: Set[str] = set()
        self._fields: Dict[str, OptionMetaData] = {}
        for app in self.apps:
            self._add_app(app)
        actions = self._create_actions()
        del self._short_names
        del self._fields
        return actions

    def tmp(self):
        #self.actions
        self.write()
