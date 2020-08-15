"""Contains a class used to create a tree of dictionaries with only Python
primitives handy for creating JSON.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Set, Union
import dataclasses
from dataclasses import dataclass, fields, Field, asdict
import sys
from io import TextIOBase
from . import Writable


@dataclass
class Dictable(Writable):
    """A class that that generates a dictionary recursively from data classes and
    primitive data structures.

    """
    @property
    def _fields(self) -> Set[Field]:
        """Keys to omit from the dictionary.

        """
        return filter(lambda f: f.repr, fields(self))

    def _from_dictable(self, obj, recurse: bool) -> Dict[str, Any]:
        dct = {}
        for f in obj._fields:
            name = f.name
            v = getattr(obj, name)
            dct[name] = obj._from_object(v, recurse)
        return dct

    def _from_dict(self, obj: dict, recurse: bool) -> Dict[str, Any]:
        dct = {}
        for k, v in obj.items():
            dct[str(k)] = self._from_object(v, recurse)
        return dct

    def _from_dataclass(self, obj: Any, recurse: bool) -> Dict[str, Any]:
        return self._from_dict(asdict(obj), recurse)

    def _format_dictable(self, obj: Any) -> Union[str, None]:
        v = None
        if hasattr(self, '_DICTABLE_FORMATS'):
            fmt_str = self._DICTABLE_FORMATS.get(type(obj))
            if fmt_str is not None:
                v = fmt_str.format(obj)
        return v

    def _format(self, obj: Any) -> str:
        v = None
        if obj is not None:
            if isinstance(obj, DICTABLE_CLASS):
                v = obj._format_dictable(obj)
            else:
                v = self._format_dictable(obj)
            if v is None:
                if isinstance(obj, (int, float, bool, str)):
                    v = obj
                else:
                    v = str(obj)
        return v

    def _from_object(self, obj: Any, recurse: bool) -> Any:
        if recurse:
            if isinstance(obj, DICTABLE_CLASS):
                ret = self._from_dictable(obj, recurse)
            elif dataclasses.is_dataclass(obj):
                ret = self._from_dataclass(obj, recurse)
            elif isinstance(obj, dict):
                ret = self._from_dict(obj, recurse)
            elif isinstance(obj, (tuple, list, set)):
                ret = list(map(lambda o: self._from_object(o, recurse), obj))
            else:
                ret = self._format(obj)
            return ret

    def asdict(self, recurse: bool = True) -> Dict[str, Any]:
        """Return the content of the object as a dictionary.

        """
        return self._from_dictable(self, recurse=recurse)

    def _get_description(self, include_type: bool = False) -> str:
        def fmap(f: Field) -> str:
            v = getattr(self, f.name)
            if isinstance(v, str):
                v = "'" + v + "'"
            else:
                v = self._format(v)
            return f'{f.name}={v}'
        v = ', '.join(map(fmap, self._fields))
        if include_type:
            v = f'{type(self).__name__}({v})'
        return v

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        super()._write_dict(self.asdict(), depth, writer)

    def __str__(self) -> str:
        return self._get_description(True)


DICTABLE_CLASS = Dictable
