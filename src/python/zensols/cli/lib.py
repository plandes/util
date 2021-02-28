"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from typing import Type
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from pathlib import Path
from zensols.config import ConfigFactory

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
class AddConfig(object):
    CLI_META = {'first_pass': True,
                'option_overrides': {'config_path': {'long_name': 'config',
                                                     'short_name': 'c'}}}
    FILE_EXT_REGEXP = re.compile(r'.+\.([a-zA-Z]+)$')

    config_factory: ConfigFactory

    config_path: Path = field(default=None)
    """The path to the configuration file."""

    def _class_for_path(self):
        ext = self.config_path.name
        m = self.FILE_EXT_REGEXP.match(ext)
        if m is not None:
            ext = m.group(1)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"using extension to map: '{ext}'")
        return ext

    def add(self):
        """Add configuration at path to the current configuration.

        :param config_path: the path to the configuration file

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'reading configuration from {self.config_path})')
        cls: Type[ConfigFactory] = self._class_for_path()
