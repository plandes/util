from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Tuple, List
from dataclasses import dataclass, field
import logging
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import (
    Configurable, ImportIniConfig, DictionaryConfig, ImportConfigFactory,
    Dictable,
)
from . import (
    ActionCliError, ActionCliFactory, ActionMetaData,
    CommandLineParser
)

logger = logging.getLogger(__name__)


@dataclass
class Command(Dictable):
    def parse(self, args: List[str]):
        pass


@dataclass
class CommandFactory(object):
    """Boots the application context from the command line.

    """
    UTIL_PACKAGE = 'zensols.util'
    """The package name of *this* utility package."""

    package_resource: PackageResource = field()
    """Package resource (i.e. zensols.someappname)."""

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    @classmethod
    def instance(cls, package_name: str, *args, **kwargs) -> CommandFactory:
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

    def create(self) -> Tuple[Command]:
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
        cli_resolver: ActionCliFactory = fac(ActionCliFactory.SECTION)
        actions: Tuple[ActionMetaData] = cli_resolver.action_meta_datas
        parser = CommandLineParser(actions, self.package_resource.version)
        parser.write_help()
        return Command()
