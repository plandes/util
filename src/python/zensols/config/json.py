"""Implementation of the JSON configurable.

"""
__author__ = 'Paul Landes'

from typing import Union, Dict, Any
from dataclasses import dataclass
import logging
from pathlib import Path
from io import TextIOBase
import json
from zensols.persist import persisted
from . import (
    ConfigurableError, ConfigurableFileNotFoundError, DictionaryConfig
)

logger = logging.getLogger(__name__)


@dataclass
class JsonConfig(DictionaryConfig):
    """A configurator that reads JSON as a two level dictionary.  The top level
    keys are the section and the values are a single depth dictionary with
    string keys and values.

    A caveat is if all the values are terminal, in which case the top level
    singleton section is ``default_section`` given in the initializer and the
    section content is the single dictionary.

    """
    def __init__(self, config_file: Union[Path, TextIOBase],
                 default_section: str = None):
        """Initialize.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param config: configures this instance (see class docs)

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        """
        super().__init__(None, default_section)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file

    def _narrow_root(self, conf: Dict[str, Any]) -> Dict[str, str]:
        if not isinstance(conf, dict):
            raise ConfigurableError(
                f'Expecting a root level dict: {self.config_file}')
        return conf

    @persisted('_config')
    def _get_config(self) -> Dict[str, Dict[str, str]]:
        if isinstance(self.config_file, TextIOBase):
            conf = json.load(self.config_file)
        else:
            if not self.config_file.is_file():
                raise ConfigurableFileNotFoundError(self.config_file)
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
