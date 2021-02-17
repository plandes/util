"""Implementation of a dictionary backing configuration.

"""
__author__ = 'Paul Landes'

from typing import Dict, Set, Any
from dataclasses import dataclass
import logging
from . import ConfigurableError, Configurable

logger = logging.getLogger(__name__)


@dataclass
class DictionaryConfig(Configurable):
    """This is a simple implementation of a dictionary backing configuration.

    """
    def __init__(self, config: Dict[str, Dict[str, str]],
                 default_expect: bool = True,
                 default_section: str = 'default',
                 default_vars: Dict[str, str] = None):
        """Initialize.

        :param default_section: default section (defaults to `default`)

        :param default_vars: use with existing configuration is not found

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        """
        super().__init__(default_expect, default_section, default_vars)
        if config is not None:
            self._dict_config = config

    def _get_config(self) -> Dict[str, Dict[str, str]]:
        return self._dict_config

    def get_options(self, section: str = None, opt_keys: Set[str] = None,
                    vars: Dict[str, str] = None) -> Dict[str, str]:
        conf = self._get_config()
        sec = conf.get(section)
        if sec is None:
            raise ConfigurableError(f'no section: {section}')
        return sec

    def has_option(self, name: str, section: str = None) -> bool:
        conf = self._get_config()
        sec = conf.get(section)
        if sec is not None:
            return sec.contains(name)
        return False

    @property
    def sections(self) -> Set[str]:
        return set(self._get_config().keys())
