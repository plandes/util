"""An implementation configuration class that holds environment variables.

"""
__author__ = 'Paul Landes'

from typing import Dict, Set
import logging
import collections
import os
from zensols.persist import persisted
from . import Configurable

logger = logging.getLogger(__name__)


class EnvironmentConfig(Configurable):
    """An implementation configuration class that holds environment variables.

    This config will need to be added to children to :class:`.ImportIniConfig`
    if used in the configuration or import sections.

    """
    def __init__(self, section_name: str = 'env', expect: bool = False,
                 map_delimiter: str = None):
        """Initialize with a string given as described in the class docs.

        :param section_name: the name of the created section with the
                             environment variables

        :param expect: whether or not to raise an error when missing
                       options for all ``get_option*`` methods

        :param map_delimiter: when given, all environment values are replaced
                              with a duplicate; set this to ``$`` when using
                              :class:`configparser.ExtendedInterpolation` for
                              environment variables such as ``PS1``

        """
        super().__init__(expect, section_name)
        self.map_delimiter = map_delimiter

    @persisted('_parsed_config')
    def _get_parsed_config(self) -> Dict[str, str]:
        """Parse the configuration string given in the initializer (see class docs).

        """
        conf = collections.defaultdict(lambda: {})
        for kv in self.config_str.split(self.option_sep):
            m = self.KEY_VAL_REGEX.match(kv)
            if m is None:
                raise ValueError(f'unexpected format: {kv}')
            sec, name, value = m.groups()
            sec = self.default_section if sec is None else sec
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'section={sec}, name={name}, value={value}')
            conf[sec][name] = value
        return conf

    @persisted('_keys')
    def _get_keys(self) -> Dict[str, str]:
        return self._get_parsed_config().keys()

    @property
    @persisted('_sections')
    def sections(self) -> Set[str]:
        return frozenset([self.default_section])

    def has_option(self, name: str, section: str = None) -> bool:
        keys = self._get_keys()
        return self.default_section == section and name in keys

    @persisted('_env_section')
    def _get_env_section(self) -> Dict[str, str]:
        opts = {}
        delim = self.map_delimiter
        if delim is not None:
            repl = f'{delim}{delim}'
        for k, v in os.environ.items():
            if delim is None:
                val = v
            else:
                val = v.replace(delim, repl)
            opts[k] = val
        return opts

    def get_options(self, section: str = None) -> Dict[str, str]:
        if section == self.default_section:
            opts = self._get_env_section()
        else:
            opts = {}
        return opts
