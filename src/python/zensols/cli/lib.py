"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Type, Any, Dict
from dataclasses import dataclass, field
from enum import Enum, auto
from io import TextIOBase
import os
import sys
import logging
import re
from pathlib import Path
from zensols.util import PackageResource
from zensols.introspect import ClassImporter
from zensols.config import (
    ConfigFactory, Configurable, DictionaryConfig, ImportIniConfig
)
from . import (
    ActionCliError, OptionMetaData, ActionMetaData,
    ApplicationObserver, Action, Application,
)

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Set of configurable log levels on the command line.  Note that we don't
    include all so as to not overwhelm the help usage.

    """
    debug = logging.DEBUG
    info = logging.INFO
    warn = logging.WARNING
    err = logging.ERROR


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    CLI_META = {'first_pass': True,  # not a separate action
                # don't add the '-l' as a short option
                'option_overrides': {'level': {'short_name': None}},
                # we configure this class, but use a better naming for
                # debugging
                'mnemonics': {'config': 'log'},
                # only set 'level' as a command line option so we can configure
                # the rest in the application context.
                'option_includes': {'level'}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

    log_name: str = field(default=None)
    """The log name space."""

    default_level: LogLevel = field(default=LogLevel.warn)
    """The level to set the root logger."""

    level: LogLevel = field(default=LogLevel.info)
    """The level to set the application logger."""

    format: str = field(default=None)
    """The format string to use for the logging system."""

    debug: bool = field(default=False)
    """Print some logging to standard out to debug this class."""

    def _to_level(self, name: str, level: Any) -> int:
        if isinstance(level, str):
            obj = LogLevel.__members__.get(level)
            if obj is None:
                raise ValueError(f'no such level for {name}: {level}')
            level = obj
        return level.value

    def _debug(self, msg: str):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(msg)
        if self.debug:
            print(msg)

    def config(self):
        """Configure the log system.

        """
        self._debug(f'configuring root logger to {self.default_level} ' +
                    f'and {self.log_name} to {self.level}')
        level: int = self._to_level('default', self.default_level)
        params = {'level': level}
        if self.format is not None:
            params['format'] = self.format.replace('%%', '%')
        self._debug(f'config log system with level {level} ' +
                    f'({self.default_level})')
        logging.basicConfig(**params)
        if self.log_name is not None:
            level: int = self._to_level('app', self.level)
            self._debug(f'setting logger {self.log_name} to {level} ' +
                        f'({self.level})')
            logging.getLogger(self.log_name).setLevel(level)


@dataclass
class ConfigurationImporter(ApplicationObserver):
    """This class imports a child configuration in to the application context.  It
    does this by:

      1. Attempt to load the configuration indicated by the ``--config``
         option.

      2. If the option doesn't exist, attempt to get the path to load from an
         environment variable (see :meth:`_get_environ_var_from_app`).

      3. Loads the *child* configuration.

      4. Copy all sections from the child configuration to :obj:`config`.

    The child configuration is one given in :obj:`CONFIG_FACTORIES`.  If the
    child has a `.conf` extension, :class:`.ImportIniConfig` is used with its
    child set as :obj:`config` so the two can reference each other at
    property/factory resolve time.

    In the case the child configuration is loaded

    """
    CONFIG_PATH_FIELD = 'config_path'
    """The field name in this class of the child configuration path."""

    CLI_META = {'first_pass': True,  # not a separate action
                # the mnemonic must be unique and used to referece the method
                'mnemonics': {'add': '_add_config_as_import'},
                # better/shorter  long name, and reserve the short name
                'option_overrides': {CONFIG_PATH_FIELD: {'long_name': 'config',
                                                         'short_name': 'c'}},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {CONFIG_PATH_FIELD}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

    FILE_EXT_REGEX = re.compile(r'.+\.([a-zA-Z]+?)$')
    """A regular expression to parse out the extension from a file name."""

    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+?)$')
    """A regular expression to parse the name from the package name for the
    environment variable that might hold the configuration
    (i.e. ``APPNAMERC``).

    """

    CONFIG_FACTORIES = {'conf': 'ImportIniConfig',
                        'yml': 'YamlConfig',
                        'json': 'JsonConfig'}
    """The configuration factory extension to clas name."""

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """

    expect: bool = field(default=True)
    """If ``True``, raise an :class:`.ActionCliError` if the option is not given.

    """

    config_path_environ_name: str = field(default=None)
    """An environment variable containing the default path to the configuration.

    """

    # name of this field must match :obj:`CONFIG_PATH_FIELD`
    config_path: Path = field(default=None)
    """The path to the configuration file."""

    def _get_environ_var_from_app(self) -> str:
        """Return the environment variable based on the name of the application.  This
        returns the :obj:`config_path_environ_name` if set, otherwise, it
        generates it based on the name returned from the packge + ``RC`` and
        capitalizes it.

        """
        if self.config_path_environ_name is not None:
            name = self.config_path_environ_name
        else:
            pkg_res: PackageResource = self._app.factory.package_resource
            name: str = pkg_res.name
            m = self.ENVIRON_VAR_REGEX.match(name)
            if m is not None:
                name = m.group(1)
            name = f'{name}rc'.upper()
        return name

    def _get_config_option(self) -> str:
        """Return the long option name (with dashes) as given on the command line.

        """
        ameta: ActionMetaData = self._action.meta_data
        ometa: OptionMetaData = ameta.options_by_dest[self.CONFIG_PATH_FIELD]
        return ometa.long_option

    def _application_created(self, app: Application, action: Action):
        """In this call back, set the app and action for using in the invocation
        :meth:`add`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _class_for_path(self) -> Type[Configurable]:
        """Return a Python class object for the configuration based on the file
        extension.

        :see: :obj:`CONFIG_FACTORIES`

        """
        ext = self.config_path.name
        m = self.FILE_EXT_REGEX.match(ext)
        if m is not None:
            ext = m.group(1)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"using extension to map: '{ext}'")
        class_str = self.CONFIG_FACTORIES.get(ext)
        if class_str is None:
            class_str = 'ImportIniConfig'
        class_name = f'zensols.config.{class_str}'
        cls = ClassImporter(class_name).get_class()
        return cls

    def _load(self):
        """Once we have the path and the class used to load the configuration, create
        the instance and load it.

        """
        cls: Type[ConfigFactory] = self._class_for_path()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'using config factory class {cls} to load: ' +
                         str(self.config_path))
        if issubclass(cls, ImportIniConfig):
            inst = cls(self.config_path, children=(self.config,))
            inst.copy_sections(self.config)
        else:
            inst = cls(self.config_path)
            inst.copy_sections(self.config)

    def add(self):
        """Add configuration at path to the current configuration.

        :param config_path: the path to the configuration file

        """
        load_config = True
        if self.config_path is None:
            name: str = self._get_environ_var_from_app()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"attempting load config from env var '{name}'")
            val: str = os.environ.get(name)
            if val is not None:
                self.config_path = Path(val)
            else:
                if self.expect:
                    lopt = self._get_config_option()
                    raise ActionCliError(f'missing option {lopt}')
                else:
                    load_config = False
        if load_config:
            self._load()


@dataclass
class PackageInfoImporter(ApplicationObserver):
    """Adds a section to the configuration with the application package
    information.  The section to add is given in :obj:`section`, and the
    key/values are:

      * **name**: the package name (:obj:`.PackageResources.name`)
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
                'mnemonics': {'add': '_add_package_info'},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

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

    def add(self):
        """Add package information to the configuration (see class docs).

        """
        pkg_res: PackageResource = self._app.factory.package_resource
        params = {'name': pkg_res.name,
                  'version': pkg_res.version}
        dconf = DictionaryConfig({self.section: params})
        dconf.copy_sections(self.config)


class ExportFormat(Enum):
    bash = auto()
    make = auto()


@dataclass
class ExportEnvironment(object):
    """The class dumps a list of bash shell export statements for sourcing in build
    shell scripts.

    """
    CLI_META = {'option_includes': {'output_path', 'output_format'},
                'option_overrides':
                {'output_path': {'long_name': 'output',
                                 'short_name': None},
                 'output_format': {'long_name': 'exportformat',
                                   'short_name': None}}}

    config: Configurable = field()

    section: str = field()
    """The section to dump as a series of export statements."""

    output_path: Path = field(default=None)
    """The output file name for the export script."""

    output_format: ExportFormat = field(default=ExportFormat.bash)
    """The output format."""

    def _write(self, writer: TextIOBase):
        exports: Dict[str, str] = self.config.populate(section=self.section)
        if self.output_format == ExportFormat.bash:
            fmt = 'export {k}="{v}"\n'
        else:
            fmt = '{k}="{v}"\n'
        for k, v in exports.asdict().items():
            writer.write(fmt.format(**{'k': k.upper(), 'v': v}))

    def export(self):
        """Create bash shell exports for shell sourcing."""
        if self.output_path is None:
            self._write(sys.stdout)
        else:
            with open(self.output_path, 'w') as f:
                self._write(f)
