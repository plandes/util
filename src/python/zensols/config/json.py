"""Implementation of the JSON configurable.

"""
__author__ = 'Paul Landes'

from typing import Union, Dict, Set, Any
from dataclasses import dataclass
import logging
from pathlib import Path
import json
from zensols.persist import persisted
from . import ConfigurableError, DictionaryConfig

logger = logging.getLogger(__name__)


@dataclass
class JsonConfig(DictionaryConfig):
    """A configurator that reads JSON.  The JSON is just a two level dictionary.
    The top level keys are the section and the values are a single depth
    dictionary with string keys and values.

    """
    def __init__(self, config_file: Union[str, Path],
                 default_expect: bool = True,
                 default_section: str = 'default',
                 default_vars: Dict[str, str] = None):
        """Initialize.

        :param config_file: the configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param default_vars: use with existing configuration is not found

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        """
        super().__init__(None, default_expect, default_section, default_vars)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file

    def _narrow_root(self, conf: Dict[str, Any]) -> Dict[str, str]:
        if not isinstance(conf, dict):
            raise ConfigurableError(
                f'expecting a root level dict: {self.config_file}')
        return conf

    @persisted('_config')
    def _get_config(self) -> Dict[str, Dict[str, str]]:
        with open(self.config_file) as f:
            conf = json.load(f)
        conf = self._narrow_root(conf)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'raw json: {conf}')
        has_terminals = True
        for k, v in conf.items():
            if isinstance(v, dict):
                has_terminals = False
                break
        if has_terminals:
            conf = {self.default_section: conf}
        return conf
