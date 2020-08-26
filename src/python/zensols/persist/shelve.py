"""Uses the ``shelve`` OS level API to CRUD binary data.

"""
__author__ = 'Paul Landes'

import logging
from typing import Any, Iterable
from dataclasses import dataclass, field
from pathlib import Path
import shelve as sh
from zensols.persist import persisted
from zensols.persist import CloseableStash

logger = logging.getLogger(__name__)


@dataclass
class ShelveStash(CloseableStash):
    """Stash that uses Python's shelve library to store key/value pairs in DBM
    databases.

    :param path: a file to be created to store and/or load for the
                 data storage
    :param writeback: the writeback parameter given to ``shelve``

    """
    path: Path
    writeback: bool = field(default=False)

    def __post_init__(self):
        self.is_open = False

    @property
    @persisted('_shelve')
    def shelve(self):
        """Return an opened shelve object.

        """
        logger.info('creating shelve data')
        fname = str(self.path.absolute())
        inst = sh.open(fname, writeback=self.writeback)
        self.is_open = True
        return inst

    def load(self, name: str) -> Any:
        if self.exists(name):
            return self.shelve[name]

    def dump(self, name, inst):
        self.shelve[name] = inst

    def exists(self, name) -> bool:
        return name in self.shelve

    def keys(self) -> Iterable[str]:
        return self.shelve.keys()

    def delete(self, name: str = None):
        "Delete the shelve data file."
        logger.info('clearing shelve data')
        self.close()
        for path in (Path(self.path.parent, self.path.name),
                     Path(self.path.parent, self.path.name + '.db')):
            logger.debug(f'clearing {path} if exists: {path.exists()}')
            if path.exists():
                path.unlink()
                break

    def close(self):
        "Close the shelve object, which is needed for data consistency."
        if self.is_open:
            logger.info('closing shelve data')
            try:
                self.shelve.close()
                self._shelve.clear()
            except Exception:
                self.is_open = False

    def clear(self):
        if self.path.exists():
            self.path.unlink()


class shelve(object):
    """Object used with a ``with`` scope that creates the closes a shelve object.

    For example, the following opens a file ``path``, sets a temporary variable
    ``stash``, prints all the data from the shelve, and then closes it.

    with shelve(path) as stash:
        for id, val in stash, 30:
            print(f'{id}: {val}')

    """
    def __init__(self, *args, **kwargs):
        self.shelve = ShelveStash(*args, **kwargs)

    def __enter__(self):
        return self.shelve

    def __exit__(self, type, value, traceback):
        self.shelve.close()
