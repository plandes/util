"""A class to diff configurations.

Using this module requires the ``deepdiff`` package::

    pip install deepdiff
"""
__author__ = 'Paul Landes'

from typing import Dict
import re
import collections
from zensols.util import APIError
from . import Configurable, DictionaryConfig


class ConfigurableDiffer(DictionaryConfig):
    """A class to diff configurations.  Each section of configuration contains
    properties of the changed options.

    """
    _SEC_PROP_REGEX = re.compile(r"^root\['(.+)'\]\['(.+)'\]$")

    def __init__(self, config_a: Configurable, config_b: Configurable,
                 change_format: str = '{} -> {}'):
        super().__init__()
        self._config_a = config_a
        self._config_b = config_b
        self._change_format = change_format
        self._init = False

    def _diff(self) -> DictionaryConfig:
        try:
            from deepdiff import DeepDiff
        except ModuleNotFoundError as e:
            m = "DeepDiff module is not installed, use: 'pip install deepdiff'"
            raise APIError(m) from e
        da = DictionaryConfig.from_config(self._config_a)
        db = DictionaryConfig.from_config(self._config_b)
        dd = DeepDiff(da.asdict(), db.asdict())
        if 'values_changed' not in dd:
            keys = ', '.join(dd.keys())
            raise APIError(f'No values changed, found keys: {keys}')
        vc = dd['values_changed']
        changes = collections.defaultdict(dict)
        for sec_prop, vals in vc.items():
            m: re.Match = self._SEC_PROP_REGEX.match(sec_prop)
            if m is None:
                raise ValueError(f'Unknown diff format: {sec_prop}')
            sec, prop = m.groups()
            cstr = self._change_format.format(
                vals['old_value'], vals['new_value'])
            changes[sec][prop] = cstr
        return DictionaryConfig(changes)

    def _get_config(self) -> Dict[str, Dict[str, str]]:
        if not self._init:
            self._dict_config = self._diff().asdict()
        self._init = True
        return super()._get_config()
