"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Any, Dict, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import os
import sys
import logging
import re
from io import TextIOBase
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import (
    Dictable, Configurable, ConfigurableFactory, DictionaryConfig
)
from . import (
    ActionCliError, ActionCli, ActionCliMethod, OptionMetaData, ActionMetaData,
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

    loggers: Dict[str, Union[str, LogLevel]] = field(default=None)
    """Additional loggers to configure."""

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
        if self.loggers is not None:
            for name, level in self.loggers.items():
                level = self._to_level(name, level)
                logging.getLogger(name).setLevel(level)


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

    The child configuration is created by :class:`.ConfigurableFactory`.  If
    the child has a `.conf` extension, :class:`.ImportIniConfig` is used with
    its child set as :obj:`config` so the two can reference each other at
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

    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+?)$')
    """A regular expression to parse the name from the package name for the
    environment variable that might hold the configuration
    (i.e. ``APPNAMERC``).

    """

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

    def _load(self):
        """Once we have the path and the class used to load the configuration, create
        the instance and load it.

        Special handling is required to make options forward *and* backward
        propogate.

        """
        # create the command line specified config
        cf = ConfigurableFactory()
        cl_config = cf.from_path(self.config_path)

        # First inject our app context (app.conf) to the command line specified
        # configuration (--config) skipping sections that have missing options.
        # Examples of those missing include cyclical dependencies such option
        # references from our app context to the command line context.
        self.config.copy_sections(cl_config, robust=True)

        # copy the command line config to our app context letting it barf with
        # any missing properties this time
        cl_config.copy_sections(self.config)

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
    # we can't use "output_format" because ListActions would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'export_output_format'
    OUTPUT_PATH = 'output_path'
    CLI_META = {'option_includes': {OUTPUT_FORMAT, OUTPUT_PATH},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'expfmt',
                                 'short_name': None},
                 OUTPUT_PATH: {'long_name': 'output',
                               'short_name': None}}}

    config: Configurable = field()

    section: str = field()
    """The section to dump as a series of export statements."""

    output_path: Path = field(default=None)
    """The output file name for the export script."""

    export_output_format: ExportFormat = field(default=ExportFormat.bash)
    """The output format."""

    def _write(self, writer: TextIOBase):
        exports: Dict[str, str] = self.config.populate(section=self.section)
        if self.export_output_format == ExportFormat.bash:
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


class ListFormat(Enum):
    """Options for outputing the action list in :class:`.ListActions`.

    """
    text = auto()
    json = auto()
    name = auto()


@dataclass
class ListActions(ApplicationObserver, Dictable):
    # we can't use "output_format" because ExportEnvironment would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'list_output_format'
    CLI_META = {'option_includes': {OUTPUT_FORMAT},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'lstfmt',
                                 'short_name': None}}}

    list_output_format: ListFormat = field(default=ListFormat.text)
    """The output format for the action listing."""

    def __post_init__(self):
        self._command_line = False

    def _application_created(self, app: Application, action: Action):
        """In this call back, set the app and action for using in the invocation
        :meth:`add`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        action_cli: ActionCli
        ac_docs: Dict[str, str] = {}
        for action_cli in self._app.factory.cli_manager.actions_ordered:
            if not action_cli.first_pass:
                meth: ActionCliMethod
                for name, meth in action_cli.methods.items():
                    meta: ActionMetaData = meth.action_meta_data
                    if self._command_line:
                        md = meta.asdict()
                        del md['first_pass']
                        ac_docs[name] = md
                    else:
                        ac_docs[name] = meta.doc
        return ac_docs

    def list(self):
        """List all actions and, depending on format, their help."""
        def list_json():
            try:
                self._command_line = True
                print(self.asjson(indent=4))
            finally:
                self._command_line = False

        {
            ListFormat.name: lambda: print('\n'.join(self.asdict().keys())),
            ListFormat.text: lambda: self.write(),
            ListFormat.json: list_json,
        }[self.list_output_format]()
