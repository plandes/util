"""Abstracts the concept of a Python ``dict`` with additional functionality.

"""
__author__ = 'Paul Landes'

from typing import Any, Iterable, Tuple, Union, Set
from dataclasses import dataclass, field, InitVar
from abc import abstractmethod, ABC, ABCMeta
import sys
import logging
import itertools as it
from pathlib import Path
from . import PersistableError

logger = logging.getLogger(__name__)


class NotPickleable(object):
    """A class marker that raises an error on attempts to :mod:`pickle` the
    instance.

    """
    def __getstate__(self):
        """
        :raises PersistableError: is raised by the :mod:`pickle` package
        """
        raise PersistableError(f'Instances are not pickleable: {type(self)}')


class chunks(object):
    """An iterable that chunks any other iterable in to chunks.  Each element
    returned is a list of elemnets of the given size or smaller.  That element
    that might be smaller is the remainer of the iterable once it is exhausted.

    """
    def __init__(self, iterable: iter, size: int, enum: bool = False):
        """Initialize the chunker.

        :param iterable: any iterable object
        :param size: the size of each chunk

        """
        self.iterable = iterable
        self.size = size
        self.enum = enum

    def __iter__(self):
        self.iterable_session = iter(self.iterable)
        return self

    def __next__(self):
        ds = []
        for e in range(self.size):
            try:
                obj = next(self.iterable_session)
            except StopIteration:
                break
            if self.enum:
                obj = (e, obj)
            ds.append(obj)
        if len(ds) == 0:
            raise StopIteration()
        return ds


class Stash(ABC):
    """A dictionary-like pure virtual class for CRUDing data, most of which read
    and write to/from the file system.  One major difference is dictionaries
    iterate over keys while stashes iterate over items, which calls
    :meth:`items`.

    Note that there are subtle differences a [Stash] and a ``dict`` when
    generating or accessing data.  For example, when indexing obtaining the
    value is sometimes *forced* by using some mechanism to create the item.
    When using ``get`` it relaxes this creation mechanism for some
    implementations.

    """
    @abstractmethod
    def load(self, name: str) -> Any:
        """Load a data value from the pickled data with key ``name``.
        Semantically, this method loads the using the stash's implementation.
        For example :class:`.DirectoryStash` loads the data from a file if it
        exists, but factory type stashes will always re-generate the data.

        :see: :meth:`get`

        """
        pass

    def get(self, name: str, default: Any = None) -> Any:
        """Load an object or a default if key ``name`` doesn't exist.
        Semantically, this method tries not to re-create the data if it already
        exists.  This means that if a stash has built-in caching mechanisms,
        this method uses it.

        :see: :meth:`load`

        """
        if self.exists(name):
            item = self.load(name)
        else:
            item = default
        return item

    def exists(self, name: str) -> bool:
        """Return ``True`` if data with key ``name`` exists.

        **Implementation note**: This :meth:`.Stash.exists` method is very
        inefficient and should be overriden.

        """
        for k in self.keys():
            if k == name:
                return True
        return False

    @abstractmethod
    def dump(self, name: str, inst: Any):
        "Persist data value ``inst`` with key ``name``."
        pass

    @abstractmethod
    def delete(self, name: str = None):
        """Delete the resource for data pointed to by ``name`` or the entire
        resource if ``name`` is not given.

        """
        pass

    def clear(self):
        """Delete all data from the from the stash.

        **Important**: Exercise caution with this method, of course.

        """
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'clearing stash {self.__class__}')
        for k in self.keys():
            if logger.isEnabledFor(logging.DEBUG):
                self._debug(f'deleting key: {k}')
            self.delete(k)

    @abstractmethod
    def keys(self) -> Iterable[str]:
        """Return an iterable of keys in the collection.

        """
        pass

    def key_groups(self, n):
        "Return an iterable of groups of keys, each of size at least ``n``."
        return chunks(self.keys(), n)

    def values(self) -> Iterable[Any]:
        """Return the values in the hash.

        """
        return map(lambda k: self.__getitem__(k), self.keys())

    def items(self) -> Tuple[str, Any]:
        """Return an iterable of all stash items."""
        return map(lambda k: (k, self.__getitem__(k)), self.keys())

    def _debug(self, msg: str):
        """Utility debugging method that adds the class name to the message to
        document the source stash.

        This makes no checks for if debugging is enabled since it is assumed
        the caller will do so for avoiding double checks of the logger level.

        """
        logger.debug(f'[{self.__class__.__name__}] {msg}')

    def __getitem__(self, key):
        item = self.get(key)
        if item is None:
            raise KeyError(key)
        return item

    def __setitem__(self, key, value):
        self.dump(key, value)

    def __delitem__(self, key):
        self.delete(key)

    def __contains__(self, key):
        return self.exists(key)

    def __iter__(self):
        return map(lambda x: (x, self.__getitem__(x),), self.keys())

    def __len__(self):
        return len(tuple(self.keys()))


@dataclass
class NoopStash(Stash):
    """A stash that does nothing.

    """
    def load(self, name: str) -> Any:
        return None

    def get(self, name: str, default: Any = None) -> Any:
        return default

    def exists(self, name: str) -> bool:
        return False

    def dump(self, name: str, inst: Any):
        pass

    def delete(self, name: str = None):
        pass

    def keys(self) -> Iterable[str]:
        return iter(())


@dataclass
class ReadOnlyStash(Stash):
    """An abstract base class for subclasses that do not support write methods
    (i.e. :meth:`dump`).  This class is useful to extend for factory type
    classes that generate data.  Paired with container classes such as
    :class:`.DictionaryStash` provide persistence in a reusable way.

    The only method that needs to be implemented is :meth:`load` and
    :meth:`keys`.  However, it is recommended to implement :meth:`exists` to
    speed things up.

    Setting attribute ``strict`` to ``True`` will raise a
    :class:`.PersistableError` for any modification attempts.  Otherwise,
    setting it to ``False`` (the default) silently ignores and does nothing on
    :meth:`.dump`, :meth:`delete` and :meth:`clear`.

    Example::

        class RangeStash(ReadOnlyStash):
            def __init__(self, n, end: int = None):
                super().__init__()
                self.n = n
                self.end = end

            def load(self, name: str) -> Any:
                if self.exists(name):
                    return name

            def keys(self) -> Iterable[str]:
                if self.end is not None:
                    return map(str, range(self.n, self.end))
                else:
                    return map(str, range(self.n))

            def exists(self, name: str) -> bool:
                n = int(name)
                if self.end is None:
                    if (n >= self.n):
                        return False
                elif (n < self.n) or (n >= self.end):
                    return False
                return True

    """
    def __post_init__(self):
        self.strict = False

    def _ro_check(self, meth: str):
        if self.strict:
            meth: str = meth.capitalize()
            raise PersistableError(
                f'{meth} not implemented for read only stashes ({type(self)}')

    def dump(self, name: str, inst: Any):
        self._ro_check('dump')

    def delete(self, name: str = None):
        self._ro_check('delete')

    def clear(self):
        self._ro_check('clear')


@dataclass
class CloseableStash(Stash):
    """Any stash that has a resource that needs to be closed.

    """
    @abstractmethod
    def close(self):
        "Close all resources created by the stash."
        pass


class DelegateDefaults(object):
    """Defaults set in :class:`.DelegateStash`.

    """
    # setting to True breaks stash reloads from ImportConfigFactory, so set to
    # True for tests etc
    CLASS_CHECK = False
    DELEGATE_ATTR = False


@dataclass
class DelegateStash(CloseableStash, metaclass=ABCMeta):
    """Delegate pattern.  It can also be used as a no-op if no delegate is
    given.

    A minimum functioning implementation needs the :meth:`load` and
    :meth:`keys` methods overriden.  Inheriting and implementing a
    :class:`.Stash` such as this is usually used as the ``factory`` in a
    :class:`.FactoryStash`.

    This class delegates attribute fetches to the delegate for the
    unimplemented methods and attributes using a decorator pattern when
    attribute :py:obj:`delegate_attr` is set to ``True``.

    **Note:** Delegate attribute fetching can cause strange and unexpected
    behavior, so use this funcationlity with care.  It is advised to leave it
    off if unexpected ``AttributeError`` are raised due to incorrect attribute
    is access or method dispatching.

    :see: :py:obj:`delegate_attr`

    """
    delegate: Stash = field()
    """The stash to delegate method invocations."""

    def __post_init__(self):
        if self.delegate is None:
            raise PersistableError('Delegate not set')
        if not isinstance(self.delegate, Stash):
            msg = f'not a stash: {self.delegate.__class__} or reloaded'
            if DelegateDefaults.CLASS_CHECK:
                raise PersistableError(msg)
            else:
                logger.warning(msg)
        self.delegate_attr = DelegateDefaults.DELEGATE_ATTR

    def __getattr__(self, attr, default=None):
        if attr == 'delegate_attr':
            return False
        if self.delegate_attr:
            try:
                delegate = super().__getattribute__('delegate')
            except AttributeError:
                raise AttributeError(
                    f"'{self.__class__.__name__}' object has no attribute " +
                    f"'{attr}'; delegate not set'")
            return delegate.__getattribute__(attr)
        else:
            return super().__getattribute__(attr)

    def _debug_meth(self, meth: str):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(
                f'calling method <{meth}> on delegate {type(self.delegate)}')

    def load(self, name: str) -> Any:
        self._debug_meth('load')
        if self.delegate is not None:
            return self.delegate.load(name)

    def get(self, name: str, default: Any = None) -> Any:
        """Load an object or a default if key ``name`` doesn't exist.

        **Implementation note:** sub classes will probably want to override
        this method given the super method is cavalier about calling
        :meth:`exists:` and :meth:`load`.  Based on the implementation, this
        can be problematic.

        """
        self._debug_meth('get')
        if self.delegate is None:
            return super().get(name, default)
        else:
            return self.delegate.get(name, default)

    def exists(self, name: str) -> bool:
        self._debug_meth('exists')
        if self.delegate is not None:
            return self.delegate.exists(name)
        else:
            return False

    def dump(self, name: str, inst):
        self._debug_meth('dump')
        if self.delegate is not None:
            return self.delegate.dump(name, inst)

    def delete(self, name=None):
        self._debug_meth('delete')
        if self.delegate is not None:
            self.delegate.delete(name)

    def keys(self) -> Iterable[str]:
        self._debug_meth('keys')
        if self.delegate is not None:
            return self.delegate.keys()
        return ()

    def clear(self):
        self._debug_meth('clear')
        if self.delegate is not None:
            if logger.isEnabledFor(logging.DEBUG):
                self._debug(
                    f'calling super clear on {self.delegate.__class__}')
            self.delegate.clear()

    def close(self):
        self._debug_meth('close')
        if self.delegate is not None:
            return self.delegate.close()


@dataclass
class ReadOnlyDelegateStash(DelegateStash, ReadOnlyStash):
    """Makes any stash read only.

    """
    def __post_init__(self):
        super().__post_init__()
        ReadOnlyStash.__post_init__(self)

    def dump(self, name: str, inst: Any):
        ReadOnlyStash.dump(self, name, inst)

    def delete(self, name: str = None):
        ReadOnlyStash.delete(self, name)

    def clear(self):
        ReadOnlyStash.clear(self)


@dataclass
class KeyLimitStash(DelegateStash):
    """A stash that limits the number of generated keys useful for debugging.

    For most stashes, this also limits the iteration output since that is based
    on key mapping.

    """
    ATTR_EXP_META = ('limit',)

    limit: int = field(default=sys.maxsize)
    """The max number of keys provided as a slice of the delegate's keys."""

    def keys(self) -> Iterable[str]:
        ks = super().keys()
        return it.islice(ks, self.limit)

    def exists(self, name: str) -> bool:
        return name in self.keys()


@dataclass
class KeySubsetStash(ReadOnlyDelegateStash):
    """A stash that exposes a subset of the keys available in the
    :obj:`delegate`.

    """
    key_subset: InitVar[Union[Path, Set[str]]] = field()
    """A subset of the keys availble.  If this is set to a
    :class:`~pathlib.Path`, then the keys are read from a newline delimited
    file.

    """
    dynamic_subset: InitVar[bool] = field()
    """Whether the delegate keys are dynamic, which forces inefficient key
    checks on the delegate.

    """
    def __post_init__(self, key_subset: Union[Path, Set[str]],
                      dynamic_subset: bool):
        super().__post_init__()
        if isinstance(key_subset, Path):
            with open(key_subset) as f:
                self._key_subset = filter(
                    lambda ln: len(ln) > 0,
                    map(str.strip, f.readlines()))
        else:
            self._key_subset = frozenset(key_subset)
        self._dynamic_subset = dynamic_subset

    def load(self, name: str) -> Any:
        if self.exists(name):
            return super().load(name)

    def get(self, name: str, default: Any = None) -> Any:
        if self.exists(name):
            return super().get(name)

    def keys(self) -> Iterable[str]:
        if self._dynamic_subset:
            return self._key_subset | super().keys()
        else:
            return self._key_subset

    def exists(self, name: str) -> bool:
        if self._dynamic_subset and not super().exists(name):
            return False
        return name in self._key_subset


@dataclass
class PreemptiveStash(DelegateStash):
    """Provide support for preemptively creating data in a stash.  It provides
    this with :obj:`has_data` and provides a means of keeping track if the data
    has yet been created.

    **Implementation note**: This stash retrieves data from the delegate
    without checking to see if it exists first since the data might not have
    been (preemptively) yet created.

    """
    def __post_init__(self):
        super().__post_init__()
        self._has_data = None

    def get(self, name: str, default: Any = None) -> Any:
        """See class doc's implementation note."""
        item = self.load(name)
        if item is None:
            item = default
        return item

    @property
    def has_data(self) -> bool:
        """Return whether or not the stash has any data available or not.

        """
        return self._calculate_has_data()

    def _calculate_has_data(self) -> bool:
        """Return ``True`` if the delegate has keys.

        """
        if self._has_data is None:
            try:
                next(iter(self.delegate.keys()))
                self._has_data = True
            except StopIteration:
                self._has_data = False
        return self._has_data

    def _reset_has_data(self):
        """Reset the state of whether the stash has data or not.

        """
        self._has_data = None

    def _set_has_data(self, has_data: bool = True):
        """Set the state of whether the stash has data or not.

        """
        self._has_data = has_data

    def clear(self):
        if logger.isEnabledFor(logging.DEBUG):
            self._debug('not clearing--has no data')
        super().clear()
        self._reset_has_data()


class Primeable(ABC):
    """Any subclass that has the ability (and need) to do preprocessing.  For
    stashes, this means processing before an CRUD method is invoked.  For all
    other classes it usually is some processing that must be done in a single
    process.

    """
    def prime(self):
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'priming {type(self)}...')


@dataclass
class PrimeableStash(Stash, Primeable):
    """Any subclass that has the ability to do processing before any CRUD method
    is invoked.

    """
    def prime(self):
        if isinstance(self, DelegateStash) and \
           isinstance(self.delegate, PrimeableStash):
            self.delegate.prime()

    def get(self, name: str, default: Any = None) -> Any:
        self.prime()
        return super().get(name, default)

    def load(self, name: str) -> Any:
        self.prime()
        return super().load(name)

    def keys(self) -> Iterable[str]:
        self.prime()
        return super().keys()


@dataclass
class PrimablePreemptiveStash(PrimeableStash, PreemptiveStash):
    """A stash that's primable and preemptive.

    """
    pass


@dataclass
class ProtectiveStash(DelegateStash):
    """A stash that guards :meth:`dump` so that when :class:`Exception` is
    raised, the instance of the exception is dumped instead the instance data.

    """
    log_errors: bool = field()
    """When ``True`` log caught exceptions as warnings."""

    def dump(self, name: str, inst: Any):
        try:
            super().dump(name, inst)
        except Exception as e:
            if self.log_errors:
                logger.warning(f"Could not dump '{name}', using as value: {e}",
                               exc_info=True)
            super().dump(name, e)


@dataclass
class FactoryStash(PreemptiveStash):
    """A stash that defers to creation of new items to another :obj:`factory`
    stash.  It does this by calling first getting the data from the
    :obj:`delegate` stash, then when it does not exist, it uses the the
    :obj:`factory` to create the data when loading with :meth:`load`.
    Similarly, when accessing with :meth:`get` or indexing, the factory created
    item is dumped back to the delegate when the delegate does not have it.

    """
    factory: Stash = field()
    """The stash used to create using ``load`` and ``keys``."""

    enable_preemptive: bool = field(default=True)
    """If ``False``, do not invoke the super class's data calculation."""

    dump_factory_nones: bool = field(default=True)
    """Whether to pass on ``None`` values to the delegate when the factory
    creates them.

    """
    force_clear_factory: bool = field(default=False)
    """When :meth:`clear` is called the :obj:`factory` stash is only cleared if
    this is set to ``True`` or the factory is not an instance of
    :class:`.ReadOnlyStash`.  Setting this to ``True`` calls
    :meth:`.Stash.clear` regardless.

    """
    def _calculate_has_data(self) -> bool:
        if self.enable_preemptive:
            return super()._calculate_has_data()
        else:
            return False

    def load(self, name: str) -> Any:
        item = super().load(name)
        if logger.isEnabledFor(logging.DEBUG):
            self._debug(f'loaded item {name} -> {type(item)}')
        if item is None:
            if logger.isEnabledFor(logging.DEBUG):
                self._debug(f'resetting data and loading from factory: {name}')
            item = self.factory.load(name)
            if item is not None or self.dump_factory_nones:
                if logger.isEnabledFor(logging.DEBUG):
                    self._debug(f'dumping {name} -> {type(item)}')
                super().dump(name, item)
                self._reset_has_data()
                if logger.isEnabledFor(logging.DEBUG):
                    self._debug(f'reset data: has_data={self.has_data}')
        return item

    def keys(self) -> Iterable[str]:
        if self.has_data:
            if logger.isEnabledFor(logging.DEBUG):
                self._debug('super (delegate) keys')
            ks = super().keys()
        else:
            if logger.isEnabledFor(logging.DEBUG):
                self._debug('factory keys')
            ks = self.factory.keys()
        return ks

    def clear(self):
        super().clear()
        if self.force_clear_factory or \
           not isinstance(self.factory, ReadOnlyStash):
            self.factory.clear()


@dataclass
class CacheFactoryStash(FactoryStash):
    """Like :class:`.FactoryStash` but suitable for :class:`.ReadOnlyStash`
    factory instances that have a defined key set and only need a backing stash
    for caching.

    """
    dump_factory_nones: bool = field(default=False)
    """Whether to pass on ``None`` values to the delegate when the factory
    creates them.

    """
    def keys(self) -> Iterable[str]:
        return self.factory.keys()

    def exists(self, name: str) -> bool:
        return self.factory.exists(name)
