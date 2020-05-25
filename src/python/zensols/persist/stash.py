"""Stash implementations.

"""
__author__ = 'Paul Landes'

import logging
from typing import List, Callable, Any, Iterable, Set, Tuple, Dict
from dataclasses import dataclass, field, InitVar
from abc import ABCMeta, abstractmethod
import collections
import parse
import pickle
from pathlib import Path
import zensols.util.time as time
from . import (
    Stash,
    ReadOnlyStash,
    DelegateStash,
    PreemptiveStash,
    PrimeableStash,
)

logger = logging.getLogger(__name__)


@dataclass
class OneShotFactoryStash(PreemptiveStash, PrimeableStash, metaclass=ABCMeta):
    """A stash that is populated by a callable or an iterable 'worker'.  The data
    is generated by the worker and dumped to the delegate.

    :param worker: either a callable (i.e. function) or an interable that
                   return tuples or lists of (key, object)

    """
    def _process_work(self):
        """Invoke the worker to generate the data and dump it to the delegate.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'processing with {type(self.worker)}')
        if callable(self.worker):
            itr = self.worker()
        else:
            itr = self.worker
        for id, obj in itr:
            self.delegate.dump(id, obj)

    def prime(self):
        has_data = self.has_data
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'asserting data: {has_data}')
        if not has_data:
            with time(f'processing work in {self}'):
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


@dataclass
class OrderedKeyStash(DelegateStash):
    """Specify an ordering to how keys in a stash are returned.  This usually also
    has an impact on the order in which values are iterated since a call to get
    the keys determins it.

    """
    ATTR_EXP_META = ('order_function',)
    order_function: Callable

    def keys(self) -> List[str]:
        keys = super().keys()
        if self.order_function:
            keys = sorted(keys, key=self.order_function)
        else:
            keys = sorted(keys)
        return keys


@dataclass
class DictionaryStash(Stash):
    """Use a dictionary as a backing store to the stash.  If one is not provided in
    the initializer a new ``dict`` is created.

    """
    _data: dict = field(default_factory=dict)

    @property
    def data(self):
        return self._data

    def load(self, name: str):
        return self.data.get(name)

    def get(self, name: str, default=None):
        return self.data.get(name, default)

    def exists(self, name: str):
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

    :param delegate: the underlying persistence stash
    :param cache_stash: a stash used for caching (defaults to
                        ``DictionaryStash``)


    """
    cache_stash: Stash = field(default_factory=lambda: DictionaryStash())

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
    """Creates a pickeled data file with a file name in a directory with a given
    pattern across all instances.

    :param path: the directory of where to store the files
    :param pattern: the file name portion with ``name`` populating to the
        key of the data value

    """
    ATTR_EXP_META = ('path', 'pattern')

    path: Path
    pattern: str = field(default='{name}.dat')

    def __post_init__(self):
        if not isinstance(self.path, Path):
            raise ValueError(
                f'expecting pathlib.Path but got: {self.path.__class__}')

    def assert_path_dir(self):
        self.path.mkdir(parents=True, exist_ok=True)

    def key_to_path(self, name: str) -> Path:
        """Return a path to the pickled data with key ``name``.

        """
        fname = self.pattern.format(**{'name': name})
        logger.debug(f'path {self.path}: {self.path.exists()}')
        self.assert_path_dir()
        return Path(self.path, fname)

    def load(self, name: str) -> Any:
        path = self.key_to_path(name)
        inst = None
        if path.exists():
            logger.info(f'loading instance from {path}')
            with open(path, 'rb') as f:
                inst = pickle.load(f)
        logger.debug(f'loaded instance: {inst}')
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

        logger.debug(f'checking path {self.path} ({type(self.path)})')
        if not self.path.is_dir():
            keys = ()
        else:
            keys = filter(lambda x: x is not None,
                          map(path_to_key, self.path.iterdir()))
        return keys

    def dump(self, name: str, inst: Any):
        logger.info(f'saving instance: {inst}')
        path = self.key_to_path(name)
        with open(path, 'wb') as f:
            pickle.dump(inst, f)

    def delete(self, name: str):
        logger.info(f'deleting instance: {name}')
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
        logger.debug(f'dumping result {self.name} to {path}')
        super().dump(key, inst)

    def load(self, name: str = None) -> Any:
        """Just like ``Stash.load``, but if the key is omitted, return the value of the
        last key in the stash.

        """
        if name is None:
            name = self.get_last_key(False)
        if len(self) > 0:
            return super().load(name)


class DirectoryCompositeStash(DirectoryStash, metaclass=ABCMeta):
    INSTANCE_DIRECTORY_NAME = 'inst'
    COMPOSITE_DIRECTORY_NAME = 'comp'

    def __init__(self, path: Path, groups: Tuple[Set[str]]):
        super().__init__(path)
        stashes = {}
        comp_path = self.path / self.COMPOSITE_DIRECTORY_NAME
        self.stash_by_group = {}
        self.stash_by_attribute = stashes
        self.path = self.path / self.INSTANCE_DIRECTORY_NAME
        self.groups = groups
        comps: Set[str]
        for group in groups:
            if not isinstance(group, set):
                raise ValueError(
                    f'composition not set: {group} ({type(group)})')
            name = '-'.join(sorted(group))
            path = comp_path / name
            comp_stash = DirectoryStash(path)
            comp_stash.group = group
            comp_stash.group_name = name
            for k in group:
                if k in stashes:
                    raise ValueError(
                        f'duplicate name \'{k}\' in {groups}')
                stashes[k] = comp_stash
                self.stash_by_group[name] = comp_stash

    @abstractmethod
    def _to_composite(self, inst: Any) -> Tuple[str, Any, Tuple[str, Any]]:
        pass

    def _dict_to_composite(self, inst: Any, attr_name: str) -> \
            Tuple[str, Any, Tuple[str, Any]]:
        data_group = collections.defaultdict(lambda: {})
        data: dict = getattr(inst, attr_name)
        is_ordered = isinstance(data, collections.OrderedDict)
        context = tuple(data.keys()) if is_ordered else None
        for k, v in data.items():
            if k not in self.stash_by_attribute:
                raise ValueError(
                    f'unmapping/grouped attribute: {k} in {self.groups}')
            stash = self.stash_by_attribute[k]
            data_group[stash.group_name][k] = v
        data_group = tuple(data_group.items())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'create group {data_group}')
        return attr_name, data, context, data_group

    def dump(self, name: str, inst: Any):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'dump {name} -> {inst}')
        attr_name, org_attr_val, context, composite = self._to_composite(inst)
        try:
            setattr(inst, attr_name, None)
            for group_name, composite_inst in composite:
                stash = self.stash_by_group[group_name]
                stash.dump(name, composite_inst)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'dump composite {group_name}/{name}: ' +
                                 f'context={context}, inst={composite_inst}')
            super().dump(name, (inst, context))
        finally:
            setattr(inst, attr_name, org_attr_val)

    @abstractmethod
    def _from_composite(self, name: str, context: Any, inst: Any) -> Any:
        pass

    def _composite_to_dict(self, name: str, attr_name: str,
                           context: Any, inst: Any) -> Any:
        comp_data = {}
        attribs = set(self.stash_by_attribute.keys())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'load inst: {inst}, attribs: {attribs}')
        for stash in self.stash_by_group.values():
            if len(stash.group & attribs) > 0:
                data = stash.load(name)
                logger.debug(f'loaded: {data}')
                comp_data.update(data)
        if context is not None:
            ordered_data = collections.OrderedDict()
            for k in context:
                if k in comp_data:
                    ordered_data[k] = comp_data[k]
            comp_data = ordered_data
        setattr(inst, attr_name, comp_data)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'comp_data: {comp_data}')
        return inst

    def load(self, name: str) -> Any:
        inst, context = super().load(name)
        return self._from_composite(name, context, inst)
