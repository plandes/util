"""Contains a class used to create a tree of dictionaries with only Python
primitives handy for creating JSON.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Iterable, Union, Tuple
import dataclasses
from dataclasses import dataclass, fields, asdict
from collections import OrderedDict
import sys
import json
from io import TextIOBase
from . import Writable, ClassResolver


@dataclass
class Dictable(Writable):
    """A class that that generates a dictionary recursively from data classes and
    primitive data structures.

    To override the default behavior of creating a dict from a
    :class:`dataclass`, override the :meth:`_from_dictable` method.

    .. document private functions
    .. automethod:: _get_dictable_attributes
    .. automethod:: _from_dictable

    """
    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        """Return human readable and attribute names.

        :return: tuples of (<human readable name>, <attribute name>)

        """
        return map(lambda f: (f.name, f.name),
                   filter(lambda f: f.repr, fields(self)))

    def _split_str_to_attributes(self, attrs: str) -> Iterable[Tuple[str, str]]:
        return map(lambda s: (s, s), attrs.split())

    def _add_class_name_param(self, class_name_param: str,
                              dct: Dict[str, Any]):
        if class_name_param is not None:
            cls = self.__class__
            dct[class_name_param] = ClassResolver.full_classname(cls)

    def _from_dictable(self, recurse: bool, readable: bool,
                       class_name_param: str = None) -> Dict[str, Any]:
        """A subclass can override this method to give create a custom specific
        dictionary to be returned from the :meth:`asjson` client access method.

        :param recurse: if ``True``, recursively create dictionary so some
                        values might be dictionaries themselves

        :param readable: use human readable and attribute keys when available

        :param class_name_param: if set, add a ``class_name_param`` key with
                                 the class's fully qualified name (includes
                                 module name)

        :return: a JSON'able tree of dictionaries with primitive data

        :see: :meth:`asjson`
        :see: :meth:`asdict`

        """
        dct = OrderedDict()
        self._add_class_name_param(class_name_param, dct)
        for readable_name, name in self._get_dictable_attributes():
            v = getattr(self, name)
            if readable:
                k = readable_name
            else:
                k = name
            dct[k] = self._from_object(v, recurse, readable)
        return dct

    def _from_dict(self, obj: dict, recurse: bool, readable: bool) -> \
            Dict[str, Any]:
        dct = {}
        for k, v in obj.items():
            dct[str(k)] = self._from_object(v, recurse, readable)
        return dct

    def _from_dataclass(self, obj: Any, recurse: bool, readable: bool) -> \
            Dict[str, Any]:
        return self._from_dict(asdict(obj), recurse, readable)

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

    def _from_object(self, obj: Any, recurse: bool, readable: bool) -> Any:
        if recurse:
            if isinstance(obj, DICTABLE_CLASS):
                ret = obj._from_dictable(recurse, readable)
            elif dataclasses.is_dataclass(obj):
                ret = self._from_dataclass(obj, recurse, readable)
            elif isinstance(obj, dict):
                ret = self._from_dict(obj, recurse, readable)
            elif isinstance(obj, (tuple, list, set)):
                ret = map(lambda o: self._from_object(o, recurse, readable),
                          obj)
                ret = list(ret)
            else:
                ret = self._format(obj)
            return ret

    def asdict(self, recurse: bool = True, readable: bool = True,
               class_name_param: str = None) -> Dict[str, Any]:
        """Return the content of the object as a dictionary.

        :param recurse: if ``True``, recursively create dictionary so some
                        values might be dictionaries themselves

        :param readable: use human readable and attribute keys when available

        :param class_name_param: if set, add a ``class_name_param`` key with
                                 the class's fully qualified name (includes
                                 module name)

        :return: a JSON'able tree of dictionaries with primitive data

        :see: :meth:`asjson`
        :see: :meth:`_from_dictable`

        """
        return self._from_dictable(recurse, readable, class_name_param)

    def asjson(self, writer: TextIOBase = None,
               recurse: bool = True, readable: bool = True, **kwargs) -> str:
        """Return a JSON string representing the data in this instance.

        """
        dct = self.asdict(recurse=recurse, readable=readable)
        if writer is None:
            return json.dumps(dct, **kwargs)
        else:
            return json.dump(dct, writer, **kwargs)

    def _get_description(self, include_type: bool = False) -> str:
        def fmap(desc: str, name: str) -> str:
            v = getattr(self, name)
            if isinstance(v, str):
                v = "'" + v + "'"
            else:
                v = self._format(v)
            return f'{desc}={v}'
        v = ', '.join(map(lambda x: fmap(*x), self._get_dictable_attributes()))
        if include_type:
            v = f'{type(self).__name__}({v})'
        return v

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        super()._write_dict(self.asdict(recurse=True, readable=True),
                            depth, writer)

    def _write_key_value(self, k: Any, v: Any, depth: int, writer: TextIOBase):
        sp = self._sp(depth)
        v = self._format(v)
        writer.write(f'{sp}{k}: {v}\n')

    def __str__(self) -> str:
        return self._get_description(True)


DICTABLE_CLASS = Dictable
