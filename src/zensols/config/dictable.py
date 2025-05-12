"""Contains a class used to create a tree of dictionaries with only Python
primitives handy for creating JSON.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Iterable, Tuple, Optional
from dataclasses import dataclass, fields, asdict, field
import dataclasses
import sys
import logging
from collections import OrderedDict
from itertools import chain
import inspect
import json
import yaml
from io import TextIOBase, StringIO
from ..introspect import ClassResolver
from ..util import Writable
from . import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class Dictable(Writable):
    """A class that that generates a dictionary recursively from data classes
    and primitive data structures.

    To override the default behavior of creating a dict from a
    :class:`dataclass`, override the :meth:`_from_dictable` method.

    In addition to the fields from the dataclass, if the attribute
    ``_DICTABLE_ATTRIBUTES`` is set, those are added as well (see
    :meth:`_get_dictable_attributes`).

    See :meth:`write` for how a dictable writes itself as a sublcass of
    :class:`.Writable` and usage of class attributes
    ``_DICTABLE_WRITABLE_DESCENDANTS`` and ``_DICTABLE_WRITE_EXCLUDES``.

    .. document private functions
    .. automethod:: _get_dictable_attributes
    .. automethod:: _from_dictable
    .. automethod:: _write_descendants
    .. automethod:: _writable_dict

    :see: :meth:`write`

    """
    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        """Return human readable and attribute names.

        :return: tuples of (<human readable name>, <attribute name>)

        """
        attrs = map(lambda f: (f.name, f.name),
                    filter(lambda f: f.repr, fields(self)))
        if hasattr(self, '_DICTABLE_ATTRIBUTES'):
            add_attrs = getattr(self, '_DICTABLE_ATTRIBUTES')
            attrs = chain.from_iterable(
                [attrs, map(lambda a: (a, a), add_attrs)])
        return attrs

    def _split_str_to_attributes(self, attrs: str) -> \
            Iterable[Tuple[str, str]]:
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'from dictable: {type(self)}')
        dct = OrderedDict()
        self._add_class_name_param(class_name_param, dct)
        for readable_name, name in self._get_dictable_attributes():
            v = getattr(self, name)
            if readable:
                k = readable_name
            else:
                k = name
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'dict: <{k}> -> {type(v)}')
            dct[k] = self._from_object(v, recurse, readable)
        return dct

    def _from_dict(self, obj: dict, recurse: bool, readable: bool) -> \
            Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'from dict: {type(obj)}')
        dct = {}
        for k, v in obj.items():
            dct[str(k)] = self._from_object(v, recurse, readable)
        return dct

    def _from_dataclass(self, obj: Any, recurse: bool, readable: bool) -> \
            Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'from dataclass: {type(obj)}')
        if not dataclasses.is_dataclass(obj):
            raise ConfigurationError(f'Not a dataclass: {obj.__class__}')
        return self._from_dict(asdict(obj), recurse, readable)

    def _format_dictable(self, obj: Any) -> Optional[str]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'format dictable: {type(obj)}')
        v = None
        if hasattr(self, '_DICTABLE_FORMATS'):
            fmt_str = self._DICTABLE_FORMATS.get(type(obj))
            if fmt_str is not None:
                v = fmt_str.format(obj)
        return v

    def _format(self, obj: Any) -> str:
        v = None
        if obj is not None:
            if isinstance(obj, _DICTABLE_CLASS):
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'from object: {type(obj)}')
        if recurse:
            if inspect.isclass(obj):
                # leave classes in tact and use JSONEncoder to convert in
                # ``asjson`` if necessary
                ret = obj
            elif isinstance(obj, _DICTABLE_CLASS):
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'asdict: {type(self)}')
        return self._from_dictable(recurse, readable, class_name_param)

    def asflatdict(self, *args, **kwargs) -> Dict[str, Any]:
        """Like :meth:`asdict` but flatten in to a data structure suitable for
        writing to JSON or YAML.

        """
        dct: Dict[str, Any] = self.asdict(*args, **kwargs)
        io = StringIO()
        json.dump(dct, io)
        io.seek(0)
        return json.load(io)

    def asjson(self, writer: TextIOBase = None, recurse: bool = True,
               readable: bool = True, flatten: bool = True, **kwargs) -> str:
        """Return a JSON string representing the data in this instance.

        """
        dct: Dict[str, Any]
        if flatten:
            dct = self.asflatdict(recurse=recurse, readable=readable)
        else:
            dct = self.asdict(recurse=recurse, readable=readable)
        if writer is None:
            return json.dumps(dct, **kwargs)
        else:
            return json.dump(dct, writer, **kwargs)

    def asyaml(self, writer: TextIOBase = None,
               recurse: bool = True, readable: bool = True, **kwargs) -> str:
        """Return a YAML string representing the data in this instance.

        """
        dct: Dict[str, Any] = self.asflatdict(
            recurse=recurse, readable=readable)
        if writer is None:
            writer = StringIO()
            yaml.dump(dct, writer, **kwargs)
            return writer.getvalue()
        else:
            return yaml.dump(dct, writer, **kwargs)

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

    def _write_descendants(self, depth: int = 0,
                           writer: TextIOBase = sys.stdout):
        """Write this instance by using the :meth:`write` method on children
        instead of writing the generated dictionary.

        """
        for readable_name, name in self._get_dictable_attributes():
            v = getattr(self, name)
            if self._is_container(v):
                self._write_line(f'{readable_name}:', depth, writer)
                self._write_object(v, depth + 1, writer)
            elif dataclasses.is_dataclass(v):
                self._write_line(f'{readable_name}:', depth, writer)
                self._write_dict(self._from_dataclass(v, True, True),
                                 depth + 1, writer)
            else:
                self._write_key_value(readable_name, v, depth, writer)

    def _writable_dict(self) -> Dict[str, Any]:
        """Return a :class:`dict` that contains what will be output when
        :meth:`write` is called.

        """
        dct = self._from_dictable(True, True)
        if hasattr(self, '_DICTABLE_WRITE_EXCLUDES'):
            for attr in getattr(self, '_DICTABLE_WRITE_EXCLUDES'):
                del dct[attr]
        return dct

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write this instance as either a :class:`Writable` or as a
        :class:`Dictable`.  If class attribute
        ``_DICTABLE_WRITABLE_DESCENDANTS`` is set as ``True``, then use the
        :meth:`write` method on children instead of writing the generated
        dictionary.  Otherwise, write this instance by first creating a ``dict``
        recursively using :meth:`asdict`, then formatting the output.

        If the attribute ``_DICTABLE_WRITE_EXCLUDES`` is set, those attributes
        are removed from what is written in the :meth:`write` method.

        Note that this attribute will need to be set in all descendants in the
        instance hierarchy since writing the object instance graph is done
        recursively.

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        """
        name = '_DICTABLE_WRITABLE_DESCENDANTS'
        if hasattr(self, name) and (getattr(self, name) is True):
            self._write_descendants(depth, writer)
        else:
            self._write_dict(self._writable_dict(), depth, writer)

    def _write_key_value(self, k: Any, v: Any, depth: int, writer: TextIOBase):
        sp = self._sp(depth)
        v = self._format(v)
        writer.write(f'{sp}{k}: {v}\n')

    def __str__(self) -> str:
        return self._get_description(True)


_DICTABLE_CLASS = Dictable


@dataclass
class DefaultDictable(Dictable):
    """A convenience utility class that provides access to methods such as
    :meth:`write` and :meth:`asjson` without needing inheritance.

    """
    data: Dict[str, Any] = field()
    """The data used to be JSON or written."""

    def _from_dictable(self, recurse: bool, readable: bool,
                       class_name_param: str = None) -> Dict[str, Any]:
        return self.data
