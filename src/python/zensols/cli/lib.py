from __future__ import annotations
"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Any, Dict, Union, List, Type
from dataclasses import dataclass, field
from enum import Enum, auto, EnumMeta
import os
import sys
import logging
from string import Template
from io import StringIO
from json import JSONEncoder
import inspect
import re
from io import TextIOBase
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import IniConfig, ImportIniConfig, raw_ini_config
from zensols.introspect import ClassImporter
from zensols.config import (
    Dictable, Configurable, ConfigurableFactory,
    DictionaryConfig, StringConfig
)
from . import (
    ActionCliError, ApplicationError, ActionCli, ActionCliMethod,
    OptionMetaData, ActionMetaData,
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


class ExportFormat(Enum):
    """The format for the environment export with the :class:`.ExportEnvironment`
    first pass application.

    """
    bash = auto()
    make = auto()


class ListFormat(Enum):
    """Options for outputing the action list in :class:`.ListActions`.

    """
    text = auto()
    json = auto()
    name = auto()


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    CLI_META = {'first_pass': True,  # not a separate action
                # don't add the '-l' as a short option
                'option_overrides': {'level': {'short_name': None}},
                # we configure this class, but use a better naming for
                # debugging
                'mnemonic_overrides': {'config': 'log'},
                'mnemonic_includes': {'config'},
                # only set 'level' as a command line option so we can configure
                # the rest in the application context.
                'option_includes': {'level'}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

    log_name: str = field(default=None)
    """The log name space."""

    default_level: LogLevel = field(default=None)
    """The level to set the root logger."""

    level: LogLevel = field(default=None)
    """The level to set the application logger."""

    default_app_level: LogLevel = field(default=LogLevel.info)
    """The default log level to set the applicatiohn logger when not given on the
    command line.

    """

    config_file: Path = field(default=None)
    """If provided, configure the log system with this configuration file."""

    format: str = field(default=None)
    """The format string to use for the logging system."""

    loggers: Dict[str, Union[str, LogLevel]] = field(default=None)
    """Additional loggers to configure."""

    debug: bool = field(default=False)
    """Print some logging to standard out to debug this class."""

    def __post_init__(self):
        if ((self.default_level is not None) or (self.format is not None)) \
           and (self.config_file is not None):
            raise ActionCliError(
                "Cannot set 'default_level' or 'format' " +
                "while setting a log configuration file 'config_file'")
        if self.default_level is None:
            self.default_level = LogLevel.warn

    def _to_level(self, name: str, level: Any) -> int:
        if isinstance(level, LogLevel):
            level = level.value
        elif isinstance(level, str):
            obj = LogLevel.__members__.get(level)
            if obj is None:
                raise ApplicationError(f'No such level for {name}: {level}')
            level = obj.value
        if not isinstance(level, int):
            raise ActionCliError(f'Unknown level: {level}({type(level)})')
        return level

    def _debug(self, msg: str):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(msg)
        if self.debug:
            print(msg)

    def _config_file(self):
        import logging.config
        self._debug(f'configuring from file: {self.config_file}')
        logging.config.fileConfig(self.config_file,
                                  disable_existing_loggers=False)

    def _config_basic(self):
        self._debug(f'configuring root logger to {self.default_level}')
        level: int = self._to_level('default', self.default_level)
        params = {'level': level}
        if self.format is not None:
            params['format'] = self.format.replace('%%', '%')
        self._debug(f'config log system with level {level} ' +
                    f'({self.default_level})')
        logging.basicConfig(**params)

    def config(self):
        """Configure the log system.

        """
        if self.config_file is not None:
            self._config_file()
        else:
            self._config_basic()
        if self.log_name is not None:
            app_level = self.default_app_level \
                if self.level is None else self.level
            level: int = self._to_level('app', app_level)
            self._debug(f'setting logger {self.log_name} to {level} ' +
                        f'({app_level})')
            logging.getLogger(self.log_name).setLevel(level)
        if self.loggers is not None:
            for name, level in self.loggers.items():
                level = self._to_level(name, level)
                assert isinstance(level, int)
                self._debug(f'setting logger: {name} -> {level}')
                logging.getLogger(name).setLevel(level)

    def __call__(self):
        self.config()


class ConfiguratorImporterTemplate(Template):
    delimiter = '^'


@dataclass
class ConfigurationImporter(ApplicationObserver):
    """This class imports a child configuration in to the application context.  It
    does this by:

      1. Attempt to load the configuration indicated by the ``--config``
         option.

      2. If the option doesn't exist, attempt to get the path to load from an
         environment variable (see :meth:`get_environ_var_from_app`).

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
                'mnemonic_overrides': {'merge': '_merge_config_as_import'},
                'mnemonic_includes': {'merge'},
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

    IMPORT_TYPE = 'import'
    """The string value of the ``type`` parameter in the section config identifying
    an :class:`.ImportIniConfig` import section.

    """

    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+?)$')
    """A regular expression to parse the name from the package name for the
    environment variable that might hold the configuration
    (i.e. ``APPNAMERC``).

    """
    name: str = field()
    """The section name."""

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """

    expect: bool = field(default=True)
    """If ``True``, raise an :class:`.ApplicationError` if the option is not given.

    """

    default: Path = field(default=None)
    """Use this file as the default when given on the command line."""

    config_path_environ_name: str = field(default=None)
    """An environment variable containing the default path to the configuration.

    """

    type: str = field(default=None)
    """The type of :class:`.Configurable` use to create in
    :class:`.ConfigurableFactory`.  If this is not provided, the factory
    decides based on the file extension.

    :see: :class:`.ConfigurableFactory`

    """

    arguments: Dict[str, Any] = field(default=None)
    """Additional arguments to pass to the :class:`.ConfigFactory` when created.

    """

    section: str = field(default=None)
    """Additional which section to load as an import.  This is only valid and used
    when :obj:`type` is set to `import`.  When it is, the section will replace
    the string ``^{config_apth}`` (and any other field in this instance using
    the same syntax) and load indicated remaining configuration using
    :class:`~zensols.config.ImportIniConfig`.

    See the `API documentation
    <https://plandes.github.io/util/doc/config.html#import-ini-configuration>`_
    for more information.

    """

    config_path_option_name: str = field(default='config_path')
    """If not ``None``, the name of the option to set in the section defined for
    this instance (section = :obj:`name`).

    """

    # name of this field must match :obj:`ConfigurationImporter.CONFIG_PATH_FIELD`
    config_path: Path = field(default=None)
    """The path to the configuration file."""

    def get_environ_var_from_app(self) -> str:
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
        :meth:`merge`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _validate(self):
        # the section attribute is only useful for ImportIniConfig imports
        if self.type != self.IMPORT_TYPE and self.section is not None:
            raise ActionCliError("Cannot have a 'section' entry " +
                                 f"without type of '{self.IMPORT_TYPE}'")

    def _populate_import_sections(self, config: Configurable) -> Configurable:
        sec: Dict[str, str] = self.config.get_options(self.section)
        secs = {}
        populated_sec = {}
        vals = self.__dict__
        for k, v in sec.items():
            populated_sec[k] = v.format(**vals)
        if 0:
            secs[self.section] = populated_sec
            secs[ImportIniConfig.IMPORT_SECTION] = {
                ImportIniConfig.SECTIONS_SECTION: self.section}
        else:
            secs[ImportIniConfig.IMPORT_SECTION] = populated_sec
            if ImportIniConfig.SECTIONS_SECTION in populated_sec:
                sub_secs: List[str] = self.config.serializer.parse_object(
                    self.config.get_option(
                        ImportIniConfig.SECTIONS_SECTION, self.section))
                for sec in sub_secs:
                    repl_sec = {}
                    secs[sec] = repl_sec
                    with raw_ini_config(config):
                        for k, v in config.get_options(sec).items():
                            tpl = ConfiguratorImporterTemplate(v)
                            repl_sec[k] = tpl.substitute(vals)
        return DictionaryConfig(secs)

    def _load(self):
        """Once we have the path and the class used to load the configuration, create
        the instance and load it.

        Special handling is required to make options forward *and* backward
        propogate.

        """
        if logger.isEnabledFor(logging.INFO):
            logger.info('configurator loading section: ' +
                        f'{self.config.config_file}:[{self.name}]')

        self._validate()
        # create the command line specified config
        do_back_copy = True
        # create a configuration factory using the configuration file extension
        if self.type is None:
            args = {} if self.arguments is None else self.arguments
            cf = ConfigurableFactory(kwargs=args)
            cl_config = cf.from_path(self.config_path)
            logger.info(f'config loaded {self.config_path} as ' +
                        f'type {cl_config.__class__.__name__}')
        # import using ImportIniConfig as a section
        elif self.type == self.IMPORT_TYPE:
            args: dict = {} if self.arguments is None else self.arguments
            ini: IniConfig = IniConfig(self.config)
            dconf: Configurable = self._populate_import_sections(ini)
            dconf.copy_sections(ini)
            with raw_ini_config(ini):
                cl_config = ImportIniConfig(
                    config_file=ini,
                    children=self._app.factory.children_configs,
                    **args)
            with raw_ini_config(cl_config):
                cl_config.copy_sections(self.config)
            do_back_copy = False
        # otherwise, use the type to tell the configuraiton factory how to
        # create it
        else:
            args = {'config_file': self.config_path}
            if self.arguments is not None:
                args.update(self.arguments)
            cf = ConfigurableFactory(kwargs=args)
            cl_config = cf.from_type(self.type)
            logger.info(f'configurator loading {self.config_path} from ' +
                        f'type {self.type}')

        # For non-import configs, first inject our app context (app.conf) to
        # the command line specified configuration (--config) skipping sections
        # that have missing options.  Examples of those missing include
        # cyclical dependencies such option references from our app context to
        # the command line context.
        if do_back_copy:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'copying app config to {cl_config}')
            #self.config.copy_sections(cl_config, robust=True)
            with raw_ini_config(self.config):
                self.config.copy_sections(cl_config)

        # copy the command line config to our app context letting it barf with
        # any missing properties this time
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'copying to app config: {cl_config}')
        #with raw_ini_config(cl_config):
        if do_back_copy:
            with raw_ini_config(cl_config):
                cl_config.copy_sections(self.config)
        #print(self.config.get_raw_str())

    def _reset(self):
        """Reset the Python logger configuration."""
        root = logging.getLogger()
        tuple(map(root.removeHandler, root.handlers[:]))
        tuple(map(root.removeFilter, root.filters[:]))

    def merge(self):
        """Merge configuration at path to the current configuration.

        :param config_path: the path to the configuration file

        """
        load_config = True
        if self.config_path is None:
            name: str = self.get_environ_var_from_app()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"attempting load config from env var '{name}'")
            val: str = os.environ.get(name)
            if val is not None:
                self.config_path = Path(val)
            elif self.default is not None:
                self.config_path = val
            else:
                if self.expect:
                    lopt = self._get_config_option()
                    raise ApplicationError(f'Missing option {lopt}')
                else:
                    load_config = False
        if load_config:
            self._load()
            if self.config_path_option_name is not None:
                self.config.set_option(
                    self.config_path_option_name,
                    f'path: {str(self.config_path)}',
                    section=self.name)

    def __call__(self):
        self.merge()


@dataclass
class ConfigurationOverrider(object):
    """Overrides configuration in the app config.  This is useful for replacing on
    a per command line invocation basis.  Examples could include changing the
    number of epochs trained for a model.

    The :obj:`override` field either contains a path to a file that contains
    the configuration file to use to clobber the given sections/values, or a
    string to be interpreted by :class:`.StringConfig`.  This determination is
    made by whether or not the string points to an existing file or directory.

    """
    OVERRIDE_PATH_FIELD = 'override'
    CLI_META = {'first_pass': True,  # not a separate action
                'mnemonic_includes': {'merge'},
                # better/shorter  long name, and reserve the short name
                'option_overrides': {OVERRIDE_PATH_FIELD:
                                     {'metavar': '<FILE|DIR|STRING>',
                                      'short_name': None}},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {OVERRIDE_PATH_FIELD}}

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """

    override: str = field(default=None)
    """A config file/dir or a comma delimited section.key=value string that
    overrides configuration."""

    def merge(self):
        """Merge the string configuration with the application context."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'overriding with: {self.override}')
        if self.override is not None:
            path = Path(self.override)
            if path.exists():
                cf = ConfigurableFactory()
                overrides = cf.from_path(path)
            else:
                overrides = StringConfig(self.override)
            self.config.merge(overrides)

    def __call__(self):
        self.merge()


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
                'mnemonic_overrides': {'add': '_add_package_info'},
                'mnemonic_includes': {'add'},
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding package section: {self.section}={params}')
        d_conf = DictionaryConfig({self.section: params})
        d_conf.copy_sections(self.config)

    def __call__(self):
        self.add()


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
                 OUTPUT_PATH: {'long_name': 'expoutput',
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
            fmt = '{k}={v}\n'
        for k, v in exports.asdict().items():
            writer.write(fmt.format(**{'k': k.upper(), 'v': v}))

    def export(self):
        """Create bash shell exports for shell sourcing."""
        if self.output_path is None:
            self._write(sys.stdout)
        else:
            with open(self.output_path, 'w') as f:
                self._write(f)

    def __call__(self):
        self.export()


@dataclass
class ListActions(ApplicationObserver, Dictable):
    """List command line actions with their help information.

    """
    # we can't use "output_format" because ExportEnvironment would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'list_output_format'
    CLI_META = {'option_includes': {OUTPUT_FORMAT},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'lstfmt',
                                 'short_name': None}}}

    list_output_format: ListFormat = field(default=ListFormat.text)
    """The output format for the action listing."""

    type_to_string: Dict[Type, str] = field(
        default_factory=lambda: {Path: 'path'})
    """Map Python type to a string used in the JSON formatted list output."""

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
        """List all actions and help."""
        class ActionEncoder(JSONEncoder):
            def default(self, obj: Any) -> str:
                if isinstance(obj, EnumMeta) or inspect.isclass(obj):
                    val = tm.get(obj)
                    if val is None:
                        val = ClassImporter.full_classname(obj)
                    return val
                return JSONEncoder.default(self, obj)

        tm = self.type_to_string

        def list_json():
            try:
                self._command_line = True
                print(self.asjson(indent=4, cls=ActionEncoder))
            finally:
                self._command_line = False

        {
            ListFormat.name: lambda: print('\n'.join(self.asdict().keys())),
            ListFormat.text: lambda: self.write(),
            ListFormat.json: list_json,
        }[self.list_output_format]()

    def __call__(self):
        self.list()
