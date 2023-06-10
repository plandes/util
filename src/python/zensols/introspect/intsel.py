"""A class that parses a slice or element of an array.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import ClassVar, Union, Any, Set, Tuple, Iterable
from ..util import APIError
import re


class IntegerSelectionError(APIError):
    """Raised for errors parsing or working with :class:`.IntegerSelection`.

    """
    pass


class IntegerSelection(object):
    """Parses an string that selects integers.  These (:obj:`kind`) include:

      * single: ``<int>``: a singleton integers
      * interval: ``<int>-<int>``: all the integers in the inclusive interval
      * list: ``<int>,<int>,...``: a comma separated list (space optional)

    To use, create it with :meth:`from_string` and use :meth:`tuple`,
    :meth:`list`, then use as an iterable.

    """
    _DICTABLE_ATTRIBUTES: ClassVar[Set[str]] = {'kind'}
    _INTEGER_REGEX: ClassVar[re.Pattern] = re.compile(r'^\d+$')
    _INTERVAL_REGEX: ClassVar[re.Pattern] = re.compile(r'^(\d+?)-(\d+)$')
    _LIST_REGEX: ClassVar[re.Pattern] = re.compile(r'^\d+(?:,\s*\d+)+$')

    def __init__(self, raw: str) -> IntegerSelection:
        """Parse an integer selection from string ``raw``."""
        v: Any = None
        if self._INTEGER_REGEX.match(raw):
            v = int(raw)
        if v is None:
            m: re.Match = self._INTERVAL_REGEX.match(raw)
            if m is not None:
                v = int(m.group(1)), int(m.group(2))
        if v is None and self._LIST_REGEX.match(raw) is not None:
            v = list(map(int, re.split(r'\s*,\s*', raw)))
        if v is None:
            raise IntegerSelectionError(f"Bad selection format: '{raw}'")
        self._select = v

    @property
    def select(self) -> Union[int, Tuple[int, int], Tuple[int]]:
        """The selection data based on what was parsed in the initializer."""
        return self._select

    @property
    def kind(self) -> str:
        """The kind of selection (see class docs)."""
        kind: str = {
            int: 'single',
            list: 'list',
            tuple: 'interval',
        }.get(type(self.select))
        if kind is None:
            raise IntegerSelectionError(
                f'Unknown selection kind: {self.select}')
        return kind

    def __iter__(self) -> Iterable[int]:
        return {
            'single': lambda: iter((self.select,)),
            'interval': lambda: iter(range(self.select[0], self.select[1] + 1)),
            'list': lambda: iter(self.select),
        }[self.kind]()

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __str__(self) -> str:
        return f'{self.select} ({self.kind})'
