"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Type, Any
from dataclasses import dataclass, field
from enum import Enum
import os
import logging
import re
from pathlib import Path
from zensols.util import PackageResource
from zensols.introspect import ClassImporter
from zensols.config import ConfigFactory, Configurable, DictionaryConfig
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
    CONFIG_PATH_FIELD = 'config_path'
    CLI_META = {'first_pass': True,
                'mnemonics': {'add': '_add_config_as_import'},
                'option_overrides': {CONFIG_PATH_FIELD: {'long_name': 'config',
                                                         'short_name': 'c'}},
                'option_includes': {'config_path'}}
    FILE_EXT_REGEX = re.compile(r'.+\.([a-zA-Z]+?)$')
    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+?)$')
    CONFIG_FACTORIES = {'conf': 'ImportIniConfig',
                        'yml': 'YamlConfig',
                        'json': 'JsonConfig'}

    config: Configurable

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
        pkg_res: PackageResource = self._app.factory.package_resource
        name: str = pkg_res.name
        m = self.ENVIRON_VAR_REGEX.match(name)
        if m is not None:
            name = m.group(1)
        name = f'{name}rc'.upper()
        return name

    def _get_config_option(self) -> str:
        ameta: ActionMetaData = self._action.meta_data
        ometa: OptionMetaData = ameta.options_by_dest[self.CONFIG_PATH_FIELD]
        return ometa.long_option

    def _application_created(self, app: Application, action: Action):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _class_for_path(self):
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
        cls: Type[ConfigFactory] = self._class_for_path()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'using config factory class {cls} to load: ' +
                         str(self.config_path))
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
    CLI_META = {'first_pass': True,
                'always_invoke': True,
                'mnemonics': {'add': '_add_package_info'},
                'option_includes': {}}

    config: Configurable

    section: str = field(default='package')
    """The name of the section to create with the package information."""

    def _application_created(self, app: Application, action: Action):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def add(self):
        """Add package information to the configuration.

        """
        pkg_res: PackageResource = self._app.factory.package_resource
        params = {'name': pkg_res.name,
                  'version': pkg_res.version}
        dconf = DictionaryConfig({self.section: params})
        dconf.copy_sections(self.config)
