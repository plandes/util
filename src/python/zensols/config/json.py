"""Implementation of the JSON configurable.

"""
__author__ = 'Paul Landes'

from typing import Union, Dict, Set
from dataclasses import dataclass
import logging
from pathlib import Path
import json
from . import ConfigurableError, Configurable

logger = logging.getLogger(__name__)


@dataclass
class JsonConfig(Configurable):
    """A configurator that reads JSON.  The JSON is just a two level dictionary.
    The top level keys are the section and the values are a single depth
    dictionary with string keys and values.

    """
    def __init__(self, config_file: Union[str, Path],
                 default_section: str = 'default',
                 default_vars: Dict[str, str] = None,
                 default_expect: bool = False):
        """Initialize.

        :param config_file: the configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param default_vars: use with existing configuration is not found

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        """
        super().__init__(default_expect, default_section, default_vars)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file

    def _get_config(self) -> Dict[str, Dict[str, str]]:
        if not hasattr(self, '_config'):
            with open(self.config_file) as f:
                self._config = json.load(f)
        return self._config

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
