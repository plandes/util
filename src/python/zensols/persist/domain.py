"""Abstracts the concept of a Python ``dict`` with additional functionality.

"""
__author__ = 'Paul Landes'

import logging
from typing import Any, Iterable, Tuple
from dataclasses import dataclass, field
from abc import abstractmethod, ABC, ABCMeta
import itertools as it
from . import PersistableError

logger = logging.getLogger(__name__)


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
    """This is a pure virtual class that represents CRUDing data that uses ``dict``
    semantics.  The data is usually CRUDed to the file system but need not be.
    Instance can be used as iterables or dicsts.  If the former, each item is
    returned as a key/value tuple.

    Note that there are subtle differences a [Stash] and a ``dict`` when
    generating or accessing data.  For example, when indexing obtaining the
    value is sometimes *forced* by using some mechanism to create the item.
    When using ``get`` it relaxes this creation mechanism for some
    implementations.

    """
    @abstractmethod
    def load(self, name: str) -> Any:
        """Load a data value from the pickled data with key ``name``.

        """
        pass

    def get(self, name: str, default=None) -> Any:
        """Load an object or a default if key ``name`` doesn't exist.

        """
        exists = self.exists(name)
        item = self.load(name)
        if not exists:
            self.dump(name, item)
        if item is None:
            item = default
        return item

    def exists(self, name: str) -> bool:
        """Return ``True`` if data with key ``name`` exists.

        *Implementation note*: This (in ``Stash``) method is very inefficient
         and should be overriden.

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
        """Delete the resource for data pointed to by ``name`` or the entire resource
        if ``name`` is not given.

        """
        pass

    def clear(self):
        """Delete all data from the from the stash.

        *Important*: Exercise caution with this method, of course.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'clearing stash {self.__class__}')
        for k in self.keys():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'deleting key: {k}')
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

    def __getitem__(self, key):
        exists = self.exists(key)
        item = self.load(key)
        if not exists:
            self.dump(key, item)
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
class ReadOnlyStash(Stash):
    """An abstract base class for subclasses that do not support write methods
    (i.e. :meth:`load`).  This class is useful to extend for factory type
    classes that generate data.  Paired with container classes such as
    :class:`.DictionaryStash` provide persistence in a reusable way.

    The only method that needs to be implemented is :meth:`load` and
    :meth:`keys`.  However, it is recommended to implement :meth:`exists` to
    speed things up.

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

    def dump(self, name: str, inst):
        if self.strict:
            raise PersistableError(
                'Dump not implemented for read only stashes')

    def delete(self, name: str = None):
        if self.strict:
            raise PersistableError(
                'Delete not implemented for read only stashes')


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
    """Delegate pattern.  It can also be used as a no-op if no delegate is given.

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
    delegate: Stash

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

    def load(self, name: str) -> Any:
        if self.delegate is not None:
            return self.delegate.load(name)

    def get(self, name: str, default=None) -> Any:
        if self.delegate is None:
            return super().get(name, default)
        else:
            return self.delegate.get(name, default)

    def exists(self, name: str) -> bool:
        if self.delegate is not None:
            return self.delegate.exists(name)
        else:
            return False

    def dump(self, name: str, inst):
        if self.delegate is not None:
            return self.delegate.dump(name, inst)

    def delete(self, name=None):
        if self.delegate is not None:
            self.delegate.delete(name)

    def keys(self) -> Iterable[str]:
        if self.delegate is not None:
            return self.delegate.keys()
        return ()

    def clear(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'delegate clear in {self.__class__}')
        super().clear()
        if self.delegate is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f'calling super clear on {self.delegate.__class__}')
            self.delegate.clear()

    def close(self):
        if self.delegate is not None:
            return self.delegate.close()


@dataclass
class KeyLimitStash(DelegateStash):
    """A stash that limits the number of generated keys useful for debugging.

    For most stashes, this also limits the iteration output since that is based
    on key mapping.

    """
    ATTR_EXP_META = ('n_limit',)

    n_limit: int

    def keys(self) -> Iterable[str]:
        ks = super().keys()
        return it.islice(ks, self.n_limit)


@dataclass
class PreemptiveStash(DelegateStash):
    """Provide support for preemptively creating data in a stash.

    """
    def __post_init__(self):
        super().__post_init__()
        self._has_data = None

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
        logger.debug('PreemptiveStash: clearing')
        if self._calculate_has_data():
            logger.debug('PreemptiveStash: has data')
            super().clear()
        self._reset_has_data()


class Primeable(ABC):
    """Any subclass that has the ability (and need) to do preprocessing.  For
    stashes, this means processing before an CRUD method is invoked.  For all
    other classes it usually is some processing that must be done in a single
    process.

    """
    def prime(self):
        pass


@dataclass
class PrimeableStash(Stash, Primeable):
    """Any subclass that has the ability to do processing before any CRUD method is
    invoked.

    """
    def prime(self):
        if isinstance(self, DelegateStash) and \
           isinstance(self.delegate, PrimeableStash):
            self.delegate.prime()


@dataclass
class FactoryStash(PreemptiveStash):
    """A stash that defers to creation of new items to another ``factory`` stash.

    """
    ATTR_EXP_META = ('enable_preemptive',)

    factory: Stash = field()
    """The stash used to create using ``load`` and ``keys``."""

    enable_preemptive: bool = field(default=True)
    """If ``False``, do not invoke the super class's data calculation."""

    def _calculate_has_data(self) -> bool:
        if self.enable_preemptive:
            return super()._calculate_has_data()
        else:
            return False

    def load(self, name: str) -> Any:
        item = super().load(name)
        if item is None:
            self._reset_has_data()
            item = self.factory.load(name)
        return item

    def keys(self) -> Iterable[str]:
        if self.has_data:
            ks = super().keys()
        else:
            ks = self.factory.keys()
        return ks
