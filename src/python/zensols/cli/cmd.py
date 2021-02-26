from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Tuple, List
from dataclasses import dataclass, field
import logging
from itertools import chain
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import (
    Configurable, ImportIniConfig, DictionaryConfig, ImportConfigFactory,
    Dictable,
)
from . import (
    ActionCliError, ActionCliManager, ActionMetaData,
    CommandLineConfig, CommandLineParser
)

logger = logging.getLogger(__name__)


@dataclass
class Command(Dictable):
    cli_manager: ActionCliManager
    parser: CommandLineParser

    def parse(self, args: List[str]):
        return self.parser.parse(args)


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

    def create(self) -> Command:
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
        cli_manager: ActionCliManager = fac(ActionCliManager.SECTION)
        actions: Tuple[ActionMetaData] = tuple(chain.from_iterable(
            map(lambda a: a.meta_datas, cli_manager.actions.values())))
        config = CommandLineConfig(actions)
        parser = CommandLineParser(config, self.package_resource.version)
        return Command(cli_manager, parser)
