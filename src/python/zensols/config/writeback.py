"""Observer pattern that write updates back to the configuration.

"""
__author__ = 'Paul Landes'

from typing import Set
from dataclasses import dataclass
import logging
from zensols.config import Configurable, ConfigFactory

logger = logging.getLogger(__name__)


@dataclass
class Writeback(object):
    DEFAULT_SKIP_ATTRIBUTES = set([ConfigFactory.NAME_ATTRIBUTE,
                                   ConfigFactory.CONFIG_ATTRIBUTE,
                                   ConfigFactory.CONIFG_FACTORY_ATTRIBUTE])
    name: str
    config: Configurable

    def _skip_attributes(self) -> Set[str]:
        return self.DEFAULT_SKIP_ATTRIBUTES

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if hasattr(self, 'config') and name not in self._skip_attributes():
            self.config.set_option(name, value, section=self.name)
