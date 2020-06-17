"""Observer pattern that write updates back to the configuration.

"""
__author__ = 'Paul Landes'

from typing import Set, Any
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

    def _get_skip_attributes(self) -> Set[str]:
        return self.DEFAULT_SKIP_ATTRIBUTES

    def _is_allowed_type(self, value: Any) -> bool:
        return self.config.serializer.is_allowed_type(value)

    def _set_option(self, name: str, value: Any):
        has_option = self.config.has_option(name, section=self.name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'set option {self.name}:{name} = ' +
                         f'{value}: {has_option}')
        if has_option:
            self.config.set_option(name, value, section=self.name)

    def __setattr__(self, name: str, value: Any):
        try:
            super().__setattr__(name, value)
        except AttributeError as e:
            raise AttributeError(
                f'can\'t set attribute \'{name}\' = {value.__class__}: {e}')
        is_skip = name in self._get_skip_attributes()
        has_config = hasattr(self, 'config')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{name}: has config: {has_config}, skip: {is_skip}' +
                         f', is allow: {self._is_allowed_type(value)}')
        if has_config and not is_skip and self._is_allowed_type(value):
            self._set_option(name, value)
