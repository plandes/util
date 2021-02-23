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

    def config(self):
        msg = (f'configuring root logger to {self.default_level} and ' +
               f'{self.log_name} to {self.level}')
        print(msg)
        logging.basicConfig(level=self.default_level)
        if self.log_name is not None:
            logging.getLogger(self.log_name).setLevel(self.level)
