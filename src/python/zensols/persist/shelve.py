"""Uses the ``shelve`` OS level API to CRUD binary data.

"""
__author__ = 'Paul Landes'

from typing import Any, Iterable, Optional, List
from dataclasses import dataclass, field
import logging
import itertools as it
from pathlib import Path
import shelve as sh
from zensols.util.tempfile import tempfile
from zensols.persist import persisted, CloseableStash

logger = logging.getLogger(__name__)


@dataclass
class ShelveStash(CloseableStash):
    """Stash that uses Python's shelve library to store key/value pairs in DBM
    databases.

    """
    path: Path = field()
    """A file to be created to store and/or load for the data storage."""

    writeback: bool = field(default=True)
    """The writeback parameter given to ``shelve``."""

    auto_close: bool = field(default=True)
    """If ``True``, close the shelve for each operation."""

    def __post_init__(self):
        self.is_open = False

    @classmethod
    def get_extension(cls) -> str:
        if not hasattr(cls, '_EXTENSION'):
            ext: Optional[str] = None
            with tempfile(create=False, remove=False) as path:
                inst = sh.open(str(path.resolve()), writeback=False)
                del_path: Path = None
                try:
                    inst.close()
                    spaths: List[Path] = path.parent.glob(path.name + '*')
                    spath: Path
                    for spath in it.islice(spaths, 1):
                        ext = spath.suffix
                        if len(ext) > 1 and ext.startswith('.'):
                            ext = ext[1:]
                        del_path = spath
                    ext = None if len(ext) == 0 else ext
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'found extension: <{ext}>')
                finally:
                    if del_path is not None:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'deleting: {del_path}')
                        del_path.unlink()
            cls._EXTENSION = ext
        return cls._EXTENSION

    @property
    @persisted('_real_path')
    def real_path(self) -> Path:
        """The path the shelve API created on this file system.  This is
        provided since :obj:`path` does *not* take in to account that some
        (G)DBM implementations add an extension and others do not This differes
        across libraries compiled against the Python interpreter and platorm.

        """
        ext = ShelveStash.get_extension()
        ext = '' if ext is None else f'.{ext}'
        return self.path.parent / f'{self.path.name}{ext}'

    @property
    @persisted('_shelve')
    def shelve(self):
        """Return an opened shelve mod:`shelve` object.

        """
        if logger.isEnabledFor(logging.DEBUG):
            exists: bool = self.real_path.exists()
            logger.debug(f'creating shelve data, exists: {exists}')
        if not self.is_open:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        fname = str(self.path.absolute())
        inst = sh.open(fname, writeback=self.writeback)
        self.is_open = True
        return inst

    def _assert_auto_close(self):
        if self.auto_close:
            self.close()

    def load(self, name: str) -> Any:
        ret = None
        if self.exists(name):
            ret = self.shelve[name]
        self._assert_auto_close()
        return ret

    def dump(self, name: str, inst: Any):
        self.shelve[name] = inst
        self._assert_auto_close()

    def exists(self, name) -> bool:
        exists = name in self.shelve
        self._assert_auto_close()
        return exists

    def keys(self) -> Iterable[str]:
        ret = self.shelve.keys()
        if self.auto_close:
            ret = tuple(ret)
        self._assert_auto_close()
        return ret

    def delete(self, name: str = None):
        "Delete the shelve data file."
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'deleting: {name}')
        if name is None:
            self.clear()
        else:
            del self.shelve[name]

    def close(self):
        "Close the shelve object, which is needed for data consistency."
        if self.is_open:
            logger.debug('closing shelve data')
            try:
                self.shelve.close()
                self._shelve.clear()
            except Exception:
                self.is_open = False

    def clear(self):
        self.close()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'clearing shelve data if exists: {self.real_path}')
        if self.real_path.exists():
            self.real_path.unlink()


class shelve(object):
    """Object used with a ``with`` scope that creates the closes a shelve
    object.  For example, the following opens a file ``path``, sets a temporary
    variable ``stash``, prints all the data from the shelve, and then closes it:

    Example::

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
