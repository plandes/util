"""Implementation classes that are used as application configuration containers
parsed from files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Set
import logging
import re
import collections
from zensols.persist import persisted
from . import Configurable

logger = logging.getLogger(__name__)


class StringConfig(Configurable):
    KEY_VAL_REGEX = re.compile(r'^(?:([^.]+)\.)?([^=]+)=(.+)$')

    def __init__(self, config_str: str, option_sep: str = ',',
                 key_value_sep: str = '=', section_sep: str = '.',
                 default_section: str = 'default',
                 default_expect: bool = False):
        super().__init__(default_expect)
        self.config_str = config_str
        self.option_sep = option_sep
        self.key_value_sep = key_value_sep
        self.sections_sep = section_sep
        self.default_section = default_section
        self.default_expect = default_expect

    @persisted('_parsed_config')
    def _get_parsed_config(self) -> Dict[str, str]:
        conf = collections.defaultdict(lambda: {})
        for kv in self.config_str.split(self.option_sep):
            #k, v = kv.split(self.key_value_sep)
            #name = k.split(self.sections_sep)
            m = self.KEY_VAL_REGEX.match(kv)
            if m is None:
                raise ValueError(f'unexpected number ({len(name)}) ' +
                                 f'key/value format: {kv}')
            sec, name, value = m.groups()
            sec = self.default_section if sec is None else sec
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'section={sec}, name={name}, value={v}')
            conf[sec][name] = value
        return conf

    @property
    @persisted('_sections')
    def sections(self) -> Set[str]:
        return set(self._get_parsed_config().keys())

    def has_option(self, name: str, section: str = None) -> bool:
        section = self.default_section if section is None else section
        return self._get_parsed_config(section)[name]

    def get_options(self, section: str = None, opt_keys: Set[str] = None,
                    vars: Dict[str, str] = None) -> Dict[str, str]:
        section = self.default_section if section is None else section
        opts = self._get_parsed_config()[section]
        if opt_keys is not None:
            opts = {k: opts[k] for k in opt_keys}
        return opts
