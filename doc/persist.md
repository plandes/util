# Persistence

This package provides two main APIs:
* A method level [persistence framework](#persisted).
* A `dict` like data structure that CRUDs data called [stashes](#stashes).


## Class Method Level

A [PersistedWork] defines a cached location any data returned by a method of a
class.  It always caches data at the instance level.  However, it can also
cache at the global level (across all instances of the class) and also pickle
as binary data files on to the file system.

An instance of a [PersistedWork] for every [@persisted] annotation given on a
method.  When the class is created, the annotation creates a new
[PersistedWork] for the method if it doesn't already exist (i.e. defined in the
class's initializer).  The first time the method is called, the method is run
to get the return value, which is then cached via the [PersistedWork] at
whatever level(s) configured, which without a definition is only class level.

Since the all subsequent calls to the method use the cached value, the method
should take no arguments.  The annotation should be used *right* before the
method definition, so it should be added after any `@property` annotation.

A class can optionally extend [PersistedContainer] to automate the process of
(de)serializing all [PersistedWork] instances safely.  This class also safely
deallocates all persisted work data that extend [Deallocatable].

Example:

```python
from pathlib import Path
from zensols.persist import PersistableContainer, PersistedWork, persisted

class SomeClass(PersistableContainer):
    def __init__(self, n):
        self.n = n
        self._counter = PersistedWork(Path('counter.dat'), self, mkdir=True)

    @property
    @persisted('_counter')
    def count(self):
        print('returning count value')
        return self.n * 2

    @property
    @persisted('_notsaved')
    def notsaved(self):
        print('returning unsaved value')
        return self.n * 3

>>> inst = SomeClass(5)
>>> print(Path('.').iterdir())
(PosixPath('example.py'),)
>>> inst.count
returning count value
10
>>> print(Path('.').iterdir())
(PosixPath('example.py'), PosixPath('counter.dat'),)
>>> inst.count
10
>>> inst.notsaved
returning unsaved value
15
>>> inst.notsaved
15
>>> inst = SomeClass(10)
>>> inst.count
10
>>> inst.notsaved
returning unsaved value
30
```

See the test case [test_persist.py](../test/python/test_persist.py) for more
examples.


# Stashes

Stashes are dictionary like classes that create, read, update and delete (CRUD)
data.  All stashes inherit from the [Stash] abstract base class and implement
four basic operations:
* **load**: creates or retries data by a key,
* **dump**: stores data by key and Python object instance or primitive,
* **delete**: create the data object by key,
* **keys**: returns all keys defined in the stash.

Every data item uses a string key, and therefore, is an associative data
structure.  However, there are iteration methods to get all values, keys (just
like `dict`) and key/value pair if used as an iterator or as items.  All
stashes are index accessible with `[]`, can be used with `len` and can
determine containment with the `in` keyword like `dict` instances.

Note that there are subtle differences a [Stash] and a `dict` when generating
or accessing data.  For example, when indexing obtaining the value is sometimes
*forced* by using some mechanism to create the item.  When using `get` it
relaxes this creation mechanism for some implementations.

Stashes are meant be implemented to do a particular task well, and then to be
*stacked* to create more complex useful data structures.  For example, you
might create a factory stash that generates data with a [DirectoryStash].

All stashes are document in the API reference, but a short list with
descriptions are given below (see the [persist submodule] API docs):
* Framework Stashes:
  * [Stash]: The abstract base class for all stash implementations.
  * [ReadOnlyStash]: An abstract base class for subclasses that do not support
    write methods.
  * [CloseableStash]: Any stash that has a resource that needs to be closed.
  * [DelegateStash]: Delegate pattern.  It can also be used as a no-op if no
	delegate is given.
  * [KeyLimitStash]: A stash that limits the number of generated keys useful
	for debugging.
  * [PreemptiveStash]: Provide support for preemptively creating data in a
	stash.
  * [PrimeableStash]: Any subclass that has the ability to do processing before
	any CRUD method is invoked.
  * [FactoryStash]: A stash that defers to creation of new items to another
    `factory` stash.
* Implementation Stashes:
  * [OneShotFactoryStash]: A stash that is populated by a callable or an
	iterable 'worker'.
  * [SortedStash]: Specify an sorting to how keys in a stash are returned.
  * [DictionaryStash]: Use a dictionary as a backing store to the stash.
  * [CacheStash]: Provide a dictionary based caching based stash.
  * [DirectoryStash]: Creates a pickled data file with a file name in a
	directory with a given pattern across all instances.
  * [IncrementKeyDirectoryStash]: A stash that increments integer value keys in
	a stash and dumps/loads using the last key available in the stash.
  * [UnionStash]: A stash joins the data of many other stashes.
  * [ShelveStash]: Stash that uses Python's shelve library to store key/value
    pairs in DBM databases.
  * [MultiProcessStash]: A stash that forks processes to process data in a
	distributed fashion.


## Complete Examples

See the [examples](../example) directory the complete code used to create the
examples in this documentation.


<!-- links -->

[@persisted]: ../api/zensols.persist.html#zensols.persist.annotation.persisted
[Deallocatable]: ../api/zensols.persist.html?#zensols.persist.dealloc.Deallocatable
[PersistableContainer]: ../api/zensols.persist.html#zensols.persist.annotation.PersistableContainer
[PersistedWork]: ../api/zensols.persist.html#zensols.persist.annotation.PersistedWork
[persist submodule]: ../api/zensols.persist.html#submodules

[Stash]: ../api/zensols.persist.html#zensols.persist.domain.Stash
[CloseableStash]: ../api/zensols.persist.html#zensols.persist.domain.CloseableStash
[ReadOnlyStash]: ../api/zensols.persist.html#zensols.persist.domain.ReadOnlyStash
[DelegateStash]: ../api/zensols.persist.html#zensols.persist.domain.DelegateStash
[KeyLimitStash]: ../api/zensols.persist.html#zensols.persist.domain.KeyLimitStash
[PreemptiveStash]: ../api/zensols.persist.html#zensols.persist.domain.PreemptiveStash
[PrimeableStash]: ../api/zensols.persist.html#zensols.persist.domain.PrimeableStash
[FactoryStash]: ../api/zensols.persist.html#zensols.persist.domain.FactoryStash

[DirectoryStash]: ../api/zensols.persist.html#zensols.persist.stash.DirectoryStash
[OneShotFactoryStash]: ../api/zensols.persist.html#zensols.persist.stash.OneShotFactoryStash
[SortedStash]: ../api/zensols.persist.html#zensols.persist.stash.SortedStash
[DictionaryStash]: ../api/zensols.persist.html#zensols.persist.stash.DictionaryStash
[CacheStash]: ../api/zensols.persist.html#zensols.persist.stash.CacheStash
[IncrementKeyDirectoryStash]: ../api/zensols.persist.html#zensols.persist.stash.IncrementKeyDirectoryStash
[UnionStash]: ../api/zensols.persist.html#zensols.persist.stash.UnionStash
[ShelveStash]: ../api/zensols.persist.html#zensols.persist.shelve.ShelveStash
[MultiProcessStash]: ../api/zensols.multi.html#zensols.multi.stash.MultiProcessStash
