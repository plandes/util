"""Utilities to silence warnings.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Dict, List, Any
import warnings
from frozendict import frozendict
from dataclasses import dataclass, field
from zensols.introspect import ClassImporter


@dataclass
class WarningSilencer(object):
    """A utility class to invoke the Python :mod:`warnings` system to suppress
    (ignore) warnings.  Both the category (warning class) and a regular
    expression can be provided.

    """
    filters: Tuple[Dict[str, str], ...] = field()
    """A tuple of dictionaries that will be given to the
    :function:`warning.filterwarnings` function.

    """
    @property
    def filter_parameters(self) -> Tuple[Dict[str, Any], ...]:
        """A list of dictionaries, each of which are used as keyword parameters
        to :function:`warning.filterwarnings`.

        """
        param_sets: List[Dict[str, Any]] = []
        params: Dict[str, Any]
        for params in self.filters:
            cat: str = params['category']
            if 'action' not in params:
                params['action'] = 'ignore'
            if cat.find('.') == -1:
                cat = f'builtins.{cat}'
            params['category'] = ClassImporter(cat, False).get_class()
            param_sets.append(frozendict(params))
        return param_sets

    def __call__(self):
        """Invoke the warnings framework to ignore everything in
        :obj:`filter_parameters`.

        """
        params: Dict[str, Any]
        for params in self.filter_parameters:
            warnings.filterwarnings(**params)
        return self
