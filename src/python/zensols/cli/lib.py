"""Various utility command line actions.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    log_name: str = field(default=None)
    """The log name space."""

    level: str = field(default='info')
    """The level to set the application logger."""

    default_level: str = field(default='warning')
    """The level to set the root logger."""

    def _to_level(self, s: str) -> int:
        return getattr(logging, s.upper())

    def config(self):
        """Configure the log system.

        """
        msg = (f'configuring root logger to {self.default_level} and ' +
               f'{self.log_name} to {self.level}')
        print(msg)
        default = self._to_level(self.default_level)
        logging.basicConfig(level=default)
        if self.log_name is not None:
            level = self._to_level(self.level)
            logging.getLogger(self.log_name).setLevel(level)
