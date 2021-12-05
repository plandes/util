"""First pass application to provide package information.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
import re
from zensols.config import Configurable, DictionaryConfig
from zensols.util import PackageResource
from .. import Action, Application, ApplicationObserver

logger = logging.getLogger(__name__)


@dataclass
class PackageInfoImporter(ApplicationObserver):
    """Adds a section to the configuration with the application package
    information.  The section to add is given in :obj:`section`, and the
    key/values are:

      * **name**: the package name (:obj:`.PackageResources.name`)
      * **short_name**: a shorter package name useful for setting in logging
        messages taken from :obj:`.PackageResources.name`
      * **version**: the package version (:obj:`.PackageResources.version`)

    This class is useful to configure the default application module given by
    the package name for the :class:`.LogConfigurator` class.

    """
    CLI_META = {'first_pass': True,  # not a separate action
                # since there are no options and this is a first pass, force
                # the CLI API to invoke it as otherwise there's no indication
                # to the CLI that it needs to be called
                'always_invoke': True,
                # the mnemonic must be unique and used to referece the method
                'mnemonic_overrides': {'add': '_add_package_info'},
                'mnemonic_includes': {'add'},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """
    _BUT_FIRST_REGEX = re.compile(r'^[^.]+\.(.+)$')

    config: Configurable = field()
    """The parent configuration, which is populated with the package
    information.

    """
    section: str = field(default='package')
    """The name of the section to create with the package information."""

    def _application_created(self, app: Application, action: Action):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _short_name(self, pkg_res: PackageResource) -> str:
        m: re.Match = self._BUT_FIRST_REGEX.match(pkg_res.name)
        return pkg_res.name if m is None else m.group(1)

    def add(self) -> Configurable:
        """Add package information to the configuration (see class docs).

        """
        pkg_res: PackageResource = self._app.factory.package_resource
        params = {'name': pkg_res.name,
                  'short_name': self._short_name(pkg_res),
                  'version': pkg_res.version}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding package section: {self.section}={params}')
        d_conf = DictionaryConfig({self.section: params})
        d_conf.copy_sections(self.config)
        return d_conf

    def __call__(self) -> Configurable:
        return self.add()
