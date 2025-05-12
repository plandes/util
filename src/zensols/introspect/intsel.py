"""A class that parses a slice or element of an array.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import ClassVar, Union, Any, Set, Tuple, Iterable, Type, List
from enum import Enum, auto
from ..util import APIError
import re


class IntegerSelectionError(APIError):
    """Raised for errors parsing or working with :class:`.IntegerSelection`.

    """
    pass


class Kind(Enum):
    """The kind of integer selection provided by :class:`.IntegerSelection`.

    """
    single = auto()
    list = auto()
    interval = auto()

    @staticmethod
    def from_class(cls: Type) -> Kind:
        kind: str = {
            int: Kind.single,
            list: Kind.list,
            tuple: Kind.interval
        }.get(cls)
        if kind is None:
            raise IntegerSelectionError(f'Unknown selection kind: {cls}')
        return kind


class IntegerSelection(object):
    """Parses an string that selects integers.  These (:obj:`kind`) include:

      * :obj:`Kind.single`: ``<int>``: a singleton integers

      * :obj:`Kind.interval`: ``<int>-<int>``: all the integers in the inclusive
        interval

      * :obj:`Kind.list`: ``<int>,<int>,...``: a comma separated list (space
        optional)

    To use, create it with :meth:`from_string` and use :meth:`tuple`,
    :meth:`list`, then use as an iterable.

    """
    INTERVAL_DELIM: ClassVar[str] = ':'
    _DICTABLE_ATTRIBUTES: ClassVar[Set[str]] = {'kind'}
    _INTEGER_REGEX: ClassVar[re.Pattern] = re.compile(r'^[-]?\d+$')
    _INTERVAL_REGEX: ClassVar[re.Pattern] = re.compile(
        r'^(\d+?)' + INTERVAL_DELIM + r'(\d+)$')
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
    def selection(self) -> Union[int, Tuple[int, int], Tuple[int]]:
        """The selection data based on what was parsed in the initializer (see
        class docs).

        """
        return self._select

    @property
    def kind(self) -> Kind:
        """The kind of selection (see class docs)."""
        return Kind.from_class(type(self.selection))

    def select(self, arr: Tuple[Any, ...]) -> List[Any, ...]:
        """Return element(s) ``arr`` based on the :obj:`selection`.

        """
        if self.kind == Kind.single:
            return [arr[self.selection]]
        elif self.kind == Kind.interval:
            return arr[self.selection[0]:self.selection[1]]
        else:
            return list(map(lambda i: arr[i], self.selection))

    def __call__(self, arr: Tuple[Any, ...]) -> Union[Any, List[Any, ...]]:
        """See :meth:`select`."""
        return self.select(arr)

    def __iter__(self) -> Iterable[int]:
        return {
            Kind.single: lambda: iter((self.selection,)),
            Kind.interval: lambda: iter(
                range(self.selection[0], self.selection[1] + 1)),
            Kind.list: lambda: iter(self.selection),
        }[self.kind]()

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __str__(self) -> str:
        return str(self.selection)
