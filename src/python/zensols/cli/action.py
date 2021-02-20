from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import (
    Configurable, ImportIniConfig, DictionaryConfig, ImportConfigFactory
)
from . import ActionCliError

logger = logging.getLogger(__name__)


@dataclass
class ActionCli(object):
    pass


@dataclass
class ActionCliFactory(object):
    """Boots the application context from the command line.

    """

    UTIL_PACKAGE = 'zensols.util'
    """The package name of *this* utility package."""

    APP_SECTION = 'app'
    """The application context section name."""

    package_resource: PackageResource = field()
    """Package resource (i.e. zensols.someappname)."""

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    @classmethod
    def instance(cls, package_name: str, *args, **kwargs) -> ActionCli:
        """"A create facade method.

        :param package_name: used to create the :obj:`package_resource`

        :param app_config_resource: see class docs

        """
        pres = PackageResource(package_name)
        return cls(pres, *args, **kwargs)

    def _get_app_context(self, app_context: Path) -> Configurable:
        pres = PackageResource(self.UTIL_PACKAGE)
        res = 'resources/app.conf'
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'looking up resource: {res} in {pres}')
        path = pres.get_path(res)
        if not path.exists():
            # this should never not happen
            raise ValueError(f'no application context found: {path}')
        logger.info(f'loading app config: {path}')
        app_conf = DictionaryConfig(
            {'import_app': {'config_file': str(app_context.absolute()),
                            'type': 'ini'}})
        return ImportIniConfig(path, children=(app_conf,))

    def create(self) -> ActionCli:
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
        inst = fac.instance(self.APP_SECTION)
        if not isinstance(inst, ActionCli):
            raise ActionCliError(
                f'wrong type of application CLI created: {type(inst)}')
        return inst
