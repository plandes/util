"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
from enum import Enum


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

    default_level: LogLevel = field(default=LogLevel.warning)
    """The level to set the root logger."""

    def to_level(self, s: str) -> int:
        """Return the integer equivalent logging level.

        :param s: the level

        """
        return getattr(logging, s.upper())

    def config(self):
        """Configure the log system.

        """
        return self.log_name, self.level, self.default_level
