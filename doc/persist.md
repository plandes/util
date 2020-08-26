# Persistence

This package provides two main APIs:
* A method level [persistence framework](#persisted).
* A `dict` like data structure that CRUDs data called [stashes](#stashes).


# Persisted

A [PersistedWork] defines a cached location any data returned by a method of a
class.  It always caches data at the instance level.  However, it can also
cache at the global level (across all instances of the class) and also pickle



# Stashes

Stashes are dictionary like classes that create, read, update and delete (CRUD)
data.  All stashes inherit from the [Stash] abstract base class and implement
four basic operations:


<!-- links -->

[Stash]: ../api/zensols.persist.html#zensols.persist.domain.Stash
[PersistedWork]: ../api/zensols.persist.html#zensols.persist.annotation.PersistedWork
