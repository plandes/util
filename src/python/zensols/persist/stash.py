"""Stash implementations.

"""
__author__ = 'Paul Landes'

import logging
from typing import Callable, Any, Iterable, Tuple
from dataclasses import dataclass, field, InitVar
from abc import ABCMeta
from itertools import chain
import parse
import pickle
from pathlib import Path
import zensols.util.time as time
from zensols.util import APIError
from . import (
    PersistableError,
    Stash,
    ReadOnlyStash,
    DelegateStash,
    PreemptiveStash,
    PrimeableStash,
)

logger = logging.getLogger(__name__)


@dataclass
class OneShotFactoryStash(PreemptiveStash, PrimeableStash, metaclass=ABCMeta):
    """A stash that is populated by a callable or an iterable *worker*.  The data
    is generated by the worker and dumped to the delegate.  This worker is
    either a callable (i.e. function) or an interable that return tuples or
    lists of (key, object)

    To use this class, this worker must be set as attribute ``worker`` or this
    class extended and ``worker`` be a property.

    """
    def _get_worker_type(self) -> str:
        """Return the type of worker.  This default implementation returns *unknown*.
        If not implemented, when :meth:`_process_work` is called, the API has
        use :func:`callable` to determine if the worker is a method or
        property.  Doing so accessing the property invoking potentially
        unecessary work.

        :return: ``u`` for unknown, ``m`` for method (callable), or ``a`` for
                 attribute or a property

        """
        return 'u'

    def _process_work(self):
        """Invoke the worker to generate the data and dump it to the delegate.

        """
        wt = self._get_worker_type()
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'processing with {type(self.worker)}: type={wt}')
        if wt == 'u':
            if callable(self.worker):
                wt = 'm'
            else:
                wt = 'a'
        if wt == 'm':
            itr = self.worker()
        elif wt == 'a':
            itr = self.worker
        else:
            raise APIError(f'Unknown worker type: {wt}')
        for id, obj in itr:
            self.delegate.dump(id, obj)

    def prime(self):
        has_data = self.has_data
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'asserting data: {has_data}')
        if not has_data:
            with time('processing work in OneShotFactoryStash'):
                self._process_work()
            self._reset_has_data()

    def get(self, name: str, default=None):
        self.prime()
        return super().get(name, default)

    def load(self, name: str):
        self.prime()
        return super().load(name)

    def keys(self) -> Iterable[str]:
        self.prime()
        return super().keys()

    def clear(self):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug('clear')
        super().clear()


@dataclass
class SortedStash(DelegateStash):
    """Specify an sorting to how keys in a stash are returned.  This usually also
    has an impact on the sort in which values are iterated since a call to get
    the keys determins it.

    """
    ATTR_EXP_META = ('sort_function',)
    sort_function: Callable = field(default=None)

    def __iter__(self):
        return map(lambda x: (x, self.__getitem__(x),), self.keys())

    def values(self) -> Iterable[Any]:
        return map(lambda k: self.__getitem__(k), self.keys())

    def items(self) -> Tuple[str, Any]:
        return map(lambda k: (k, self.__getitem__(k)), self.keys())

    def keys(self) -> Iterable[str]:
        keys = super().keys()
        if self.sort_function is None:
            keys = sorted(keys)
        else:
            keys = sorted(keys, key=self.sort_function)
        return keys


@dataclass
class DictionaryStash(Stash):
    """Use a dictionary as a backing store to the stash.  If one is not provided in
    the initializer a new ``dict`` is created.

    """
    _data: dict = field(default_factory=dict)
    """The backing dictionary for the stash data."""

    @property
    def data(self):
        return self._data

    def load(self, name: str) -> Any:
        return self.data.get(name)

    def get(self, name: str, default=None) -> Any:
        return self.data.get(name, default)

    def exists(self, name: str) -> bool:
        return name in self.data

    def dump(self, name: str, inst):
        self.data[name] = inst

    def delete(self, name=None):
        del self.data[name]

    def keys(self):
        return self.data.keys()

    def clear(self):
        self.data.clear()
        super().clear()

    def __getitem__(self, key):
        return self.data[key]


@dataclass
class CacheStash(DelegateStash):
    """Provide a dictionary based caching based stash.

    """
    cache_stash: Stash = field(default_factory=lambda: DictionaryStash())
    """A stash used for caching (defaults to :class:`.DictionaryStash`)."""

    def load(self, name: str):
        if self.cache_stash.exists(name):
            return self.cache_stash.load(name)
        else:
            obj = self.delegate.load(name)
            self.cache_stash.dump(name, obj)
            return obj

    def exists(self, name: str):
        return self.cache_stash.exists(name) or self.delegate.exists(name)

    def delete(self, name=None):
        if self.cache_stash.exists(name):
            self.cache_stash.delete(name)
        if not isinstance(self.delegate, ReadOnlyStash):
            self.delegate.delete(name)

    def clear(self):
        if not isinstance(self.delegate, ReadOnlyStash):
            super().clear()
        self.cache_stash.clear()


@dataclass
class DirectoryStash(Stash):
    """Creates a pickled data file with a file name in a directory with a given
    pattern across all instances.

    """
    ATTR_EXP_META = ('path', 'pattern')

    path: Path = field()
    """The directory of where to store the files."""

    pattern: str = field(default='{name}.dat')
    """The file name portion with ``name`` populating to the key of the data
    value.

    """
    def __post_init__(self):
        if not isinstance(self.path, Path):
            raise PersistableError(
                f'Expecting pathlib.Path but got: {self.path.__class__}')

    def assert_path_dir(self):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'path {self.path}: {self.path.exists()}')
        self.path.mkdir(parents=True, exist_ok=True)

    def key_to_path(self, name: str) -> Path:
        """Return a path to the pickled data with key ``name``.

        """
        fname = self.pattern.format(**{'name': name})
        self.assert_path_dir()
        return Path(self.path, fname)

    def load(self, name: str) -> Any:
        path = self.key_to_path(name)
        inst = None
        if path.exists():
            if logger.isEnabledFor(logging.DEBUG):
                self._debug(f'loading instance from {path}')
            with open(path, 'rb') as f:
                inst = pickle.load(f)
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'loaded instance: {name} -> {type(inst)}')
        return inst

    def exists(self, name) -> bool:
        path = self.key_to_path(name)
        return path.exists()

    def keys(self) -> Iterable[str]:
        def path_to_key(path):
            p = parse.parse(self.pattern, path.name)
            # avoid files that don't match the pattern
            if p is not None:
                p = p.named
                if 'name' in p:
                    return p['name']

        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'checking path {self.path} ({type(self)})')
        if not self.path.is_dir():
            keys = ()
        else:
            keys = filter(lambda x: x is not None,
                          map(path_to_key, self.path.iterdir()))
        return keys

    def dump(self, name: str, inst: Any):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'saving instance: {name} -> {type(inst)}')
        path = self.key_to_path(name)
        with open(path, 'wb') as f:
            pickle.dump(inst, f)

    def delete(self, name: str):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'deleting instance: {name}')
        path = self.key_to_path(name)
        if path.exists():
            path.unlink()

    def close(self):
        pass


@dataclass
class IncrementKeyDirectoryStash(DirectoryStash):
    """A stash that increments integer value keys in a stash and dumps/loads using
    the last key available in the stash.

    """
    name: InitVar[str] = field(default='data')
    """The name of the :obj:`pattern` to use in the super class."""

    def __post_init__(self, name: str):
        super().__post_init__()
        self.pattern = name + '-{name}.dat'
        self._last_key = None

    def get_last_key(self, inc: bool = False) -> str:
        """Get the last available (highest number) keys in the stash.

        """
        if self._last_key is None:
            keys = tuple(map(int, self.keys()))
            if len(keys) == 0:
                key = 0
            else:
                key = max(keys)
            self._last_key = key
        if inc:
            self._last_key += 1
        return str(self._last_key)

    def keys(self) -> Iterable[str]:
        def is_good_key(data):
            try:
                int(data)
                return True
            except ValueError:
                return False

        return filter(is_good_key, super().keys())

    def dump(self, name_or_inst, inst=None):
        """If only one argument is given, it is used as the data and the key name is
        derived from ``get_last_key``.

        """
        if inst is None:
            key = self.get_last_key(True)
            inst = name_or_inst
        else:
            key = name_or_inst
        path = self.key_to_path(key)
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'dumping result {self.name} to {path}')
        super().dump(key, inst)

    def load(self, name: str = None) -> Any:
        """Just like ``Stash.load``, but if the key is omitted, return the value of the
        last key in the stash.

        """
        if name is None:
            name = self.get_last_key(False)
        if len(self) > 0:
            return super().load(name)


@dataclass
class UnionStash(ReadOnlyStash):
    """A stash joins the data of many other stashes.

    """
    stashes: Tuple[Stash] = field()
    """The delegate constituent stashes used for each operation."""

    def load(self, name: str) -> Any:
        item = None
        for stash in self.stashes:
            item = stash.load(name)
            if item is not None:
                break
        return item

    def get(self, name: str, default=None) -> Any:
        return self.load(name)

    def values(self) -> Iterable[Any]:
        return chain.from_iterable(map(lambda s: s.values(), self.stashes))

    def keys(self) -> Iterable[str]:
        return chain.from_iterable(map(lambda s: s.keys(), self.stashes))

    def exists(self, name: str) -> bool:
        for stash in self.stashes:
            if stash.exists(name):
                return True
        return False
