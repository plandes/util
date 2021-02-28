"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Type
from dataclasses import dataclass, field
from enum import Enum
import os
import logging
import re
from pathlib import Path
from zensols.util import PackageResource
from zensols.introspect import ClassImporter
from zensols.config import ConfigFactory, Configurable
from . import (
    ActionCliError, OptionMetaData, ActionMetaData,
    ApplicationObserver, Action, Application,
)

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    debug = logging.DEBUG
    info = logging.INFO
    warning = logging.WARNING
    error = logging.ERROR


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    log_name: str = field(default=None)
    """The log name space."""

    level: LogLevel = field(default=LogLevel.info)
    """The level to set the application logger."""

    default_level: str = field(default=LogLevel.warning)
    """The level to set the root logger."""

    def to_level(self, s: str) -> int:
        """Return the integer equivalent logging level.

        :param s: the level

        """
        return getattr(logging, s.upper())

    def config(self):
        """Configure the log system.

        """
        msg = (f'configuring root logger to {self.default_level} and ' +
               f'{self.log_name} to {self.level}')
        logger.info(msg)
        default = self.to_level(self.default_level)
        logging.basicConfig(level=default)
        if self.log_name is not None:
            level = self.to_level(self.level)
            logging.getLogger(self.log_name).setLevel(level)


@dataclass
class AddConfig(ApplicationObserver):
    CONFIG_PATH_FIELD = 'config_path'
    CLI_META = {'first_pass': True,
                'option_overrides': {CONFIG_PATH_FIELD: {'long_name': 'config',
                                                         'short_name': 'c'}},
                'option_includes': {'config_path'}}
    FILE_EXT_REGEX = re.compile(r'.+\.([a-zA-Z]+)$')
    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+)$')
    CONFIG_FACTORIES = {'conf': 'ImportIniConfig',
                        'yml': 'YamlConfig',
                        'json': 'JsonConfig'}

    config: Configurable

    expect_path: bool = field(default=True)
    """If ``True``, raise an :class:`.ActionCliError` if the option is not given.

    """

    config_path_environ_name: str = field(default=None)
    """An environment variable containing the default path to the configuration.

    """

    config_path: Path = field(default=None)
    """The path to the configuration file.

    The name of this field must match :obj:`CONFIG_PATH_FIELD`.

    """

    def _get_environ_var_from_app(self) -> str:
        pkg_res: PackageResource = self._app.factory.package_resource
        name: str = pkg_res.name
        m = self.ENVIRON_VAR_REGEX.match(name)
        if m is not None:
            name = m.group(1)
        name = f'{name}rc'.upper()
        return name

    def _get_config_option(self) -> str:
        ameta: ActionMetaData = self._action.action_meta_data
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
        if self.config_path is None:
            name: str = self._get_environ_var_from_app()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"attempting load config from env var '{name}'")
            val: str = os.environ.get(name)
            if val is not None:
                self.config_path = Path(val)
            elif self.expect_path:
                lopt = self._get_config_option()
                raise ActionCliError(f'missing option {lopt}')
        self._load()
