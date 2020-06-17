"""Observer pattern that write updates back to the configuration.

"""
__author__ = 'Paul Landes'

from typing import Set, Any
from dataclasses import dataclass
import logging
from itertools import chain
from zensols.config import Configurable, ConfigFactory

logger = logging.getLogger(__name__)


@dataclass
class Writeback(object):
    DEFAULT_SKIP_ATTRIBUTES = set([ConfigFactory.NAME_ATTRIBUTE,
                                   ConfigFactory.CONFIG_ATTRIBUTE,
                                   ConfigFactory.CONIFG_FACTORY_ATTRIBUTE])
    DEFAULT_ALLOW_TYPES = set([str, int, float, bool, list, tuple, dict])
    name: str
    config: Configurable

    def _get_skip_attributes(self) -> Set[str]:
        return self.DEFAULT_SKIP_ATTRIBUTES

    def _get_allow_types(self) -> Set[type]:
        return self.DEFAULT_ALLOW_TYPES

    def _is_allow_type(self, value: Any) -> bool:
        if isinstance(value, tuple) or isinstance(value, list):
            for i in value:
                if not self._is_allow_type(i):
                    return False
            return True
        elif isinstance(value, dict):
            for i in chain.from_iterable(value.items()):
                if not self._is_allow_type(i):
                    return False
            return True
        return value.__class__ in self._get_allow_types()

    def _set_option(self, name: str, value: Any):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'set option {self.name}:{name} = {value}')
        if self.config.has_option(name, section=self.name):
            self.config.set_option(name, value, section=self.name)

    def __setattr__(self, name: str, value: Any):
        try:
            super().__setattr__(name, value)
        except AttributeError as e:
            raise AttributeError(
                f'can\'t set attribute \'{name}\' = {value.__class__}: {e}')
        skip_attribs = self._get_skip_attributes()
        if hasattr(self, 'config') and \
           name not in skip_attribs and \
           self._is_allow_type(value):
            self._set_option(name, value)
