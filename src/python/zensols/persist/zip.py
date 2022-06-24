"""A stash that accesses a zip file.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Union
from dataclasses import dataclass
from zipfile import ZipFile
from pathlib import Path
from . import PersistableError, persisted, PersistedWork, ReadOnlyStash


@dataclass(init=False)
class ZipStash(ReadOnlyStash):
    """Acesss a zip file by using the entry file names as keys and the content of
    the entries as items.  The returned items are either byte arrays if created
    without an encoding, otherwise decode strings are returned.

    A root path can be specified so the zip file appears to have been created
    in a sub-directory.

    *Implementation note*: keys are cached to speed up access and cleared if
     the path set on the instance.

    """
    def __init__(self, path: Path, root: str = None, encoding: str = None):
        """See class docs.

        :param path: the zip file path

        :param root: the sub-directory in the zip file to base look ups (see
                     class doc)

        :param encoding: if provided, returned items will be strings decoded
                         with this encoding (such as ``utf-8``)

        """
        super().__init__()
        if root is not None and (root.startswith('/') or root.endswith('/')):
            raise PersistableError(
                f"Roots can not start or end with '/': {root}")
        self._path = path
        self._root = root
        self._encoding = encoding
        self._keys = PersistedWork('_keys', self)

    @property
    def path(self) -> Path:
        """The zip file path."""
        return self._path

    @path.setter
    def path(self, path: Path):
        """The zip file path."""
        self._path = path
        self._keys.clear()

    def _map_name(self, name: str):
        """Create an absolute entry name from the item name (key)."""
        if self._root is not None:
            name = self._root + '/' + name
        return name

    def load(self, name: str) -> Union[bytearray, str]:
        if name in self._key_set():
            name = self._map_name(name)
            with ZipFile(self.path) as z:
                with z.open(name) as myfile:
                    inst: bytearray = myfile.read()
            if self._encoding is not None:
                inst = inst.decode(self._encoding)
            return inst

    def keys(self) -> Iterable[str]:
        return iter(self._key_set())

    @persisted('_key_set_pw')
    def _key_set(self) -> Iterable[str]:
        root = self._root
        rlen = None if self._root is None else len(root)
        keys = []
        with ZipFile(self.path) as z:
            keys.extend(filter(lambda n: not n.endswith('/'), z.namelist()))
        if self._root is not None:
            keys = map(lambda k: k[rlen+1:] if k.startswith(root) else None,
                       keys)
            keys = filter(lambda k: k is not None, keys)
        return set(keys)

    def exists(self, name: str) -> bool:
        return name in self._key_set()
