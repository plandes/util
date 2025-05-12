"""Utility persistence classes.

"""
__author__ = 'Paul Landes'

from typing import Set, Iterable, Any
from dataclasses import dataclass, field
from pathlib import Path
from ..util.fail import Failure
from . import PersistedWork, persisted, DelegateStash, PrimeableStash


@dataclass
class FailureFilterStash(DelegateStash, PrimeableStash):
    """Filter's instances of :class:`~.zensols.util.fail.Failure`.  It does this
    by reading all load all items of the :obj:`delegate` stash and tracking the
    keys of which are failures.

    """
    key_path: Path = field()
    """The path of the file where valid keys are stored."""

    def __post_init__(self):
        super().__post_init__()
        self._valid_keys = PersistedWork(self.key_path, self, mkdir=True)

    @persisted('_valid_keys')
    def _get_valid_keys(self) -> Set[str]:
        valid_keys: Set[str] = set()
        for k, v in self.delegate.items():
            if not isinstance(v, Failure):
                valid_keys.add(k)
        return frozenset(valid_keys)

    def load(self, name: str) -> Any:
        self.prime()
        return super().load(name)

    def keys(self) -> Iterable[str]:
        self.prime()
        return self._get_valid_keys()

    def exists(self, name: str) -> bool:
        self.prime()
        return name in self._get_valid_keys()
