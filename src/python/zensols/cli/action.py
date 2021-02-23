from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Any, Dict, Tuple, Iterable, Set, List
from dataclasses import dataclass, field
import dataclasses
import logging
from pathlib import Path
from zensols.util import (
    PackageResource, DataClassInspector, DataClassMetaData, FieldMetaData
)
from zensols.config import (
    Configurable, Dictable, ImportIniConfig, DictionaryConfig,
    ConfigFactory, ImportConfigFactory, ClassImporter,
)
from . import ActionCliError, OptionMetaData, ActionMetaData

logger = logging.getLogger(__name__)


class ActionCliFactoryError(ActionCliError):
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
        if fmd.kwargs is not None:
            default = fmd.kwargs.get('default')
        return OptionMetaData(
            long_name=long_name,
            short_name=short_name,
            dest=fmd.name,
            dtype=eval(fmd.dtype),
            default=default,
            doc=fmd.doc)

    def _add_action_meta(self, meta: ActionCliMetaData):
        if meta.name in self.meta_datas:
            raise ActionCliFactoryError(
                f'duplicate meta data: {meta.name}')
        for name, fmd in meta.class_meta.fields.items():
            omd = self._create_option_meta_data(fmd)
            prexist = self._fields.get(fmd.name)
            if prexist is not None and omd != prexist:
                raise ActionCliFactoryError(
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


@dataclass
class ActionCliFactory(object):
    """Boots the application context from the command line.

    """

    UTIL_PACKAGE = 'zensols.util'
    """The package name of *this* utility package."""

    package_resource: PackageResource = field()
    """Package resource (i.e. zensols.someappname)."""

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    @classmethod
    def instance(cls, package_name: str, *args, **kwargs) -> ActionCliFactory:
        """"A create facade method.

        :param package_name: used to create the :obj:`package_resource`

        :param app_config_resource: see class docs

        """
        pres = PackageResource(package_name)
        return cls(pres, *args, **kwargs)

    def _get_app_context(self, app_context: Path) -> Configurable:
        pres = PackageResource(self.UTIL_PACKAGE)
        res = 'resources/app.conf'
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'looking up resource: {res} in {pres}')
        path = pres.get_path(res)
        if not path.exists():
            # this should never not happen
            raise ValueError(f'no application context found: {path}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'loading app config: {path}')
        app_conf = DictionaryConfig(
            {'import_app': {'config_file': str(app_context.absolute()),
                            'type': 'ini'}})
        return ImportIniConfig(path, children=(app_conf,))

    def create(self) -> Tuple[Any]:
        """Create the action CLI application.

        :raises ActionCliError: for any missing or misconfigurations

        """
        path = self.package_resource.get_path(self.app_config_resource)
        if not path.exists():
            raise ActionCliError(
                f"application context resource '{self.app_config_resource}' " +
                f'not found in {self.package_resource}')
        config = self._get_app_context(path)
        fac = ImportConfigFactory(config)
        cli_resolver: ActionCliResolver = fac(ActionCliResolver.SECTION)
        cli_resolver.tmp()
