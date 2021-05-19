"""A class that allows human readable information (sometimes debugging) output
with a hierarchical structure.

"""
__author__ = 'Paul Landes'

from typing import Union, Any, Iterable
from abc import ABC, abstractmethod
import sys
import logging
from logging import Logger
from collections import OrderedDict
import itertools as it
from io import TextIOBase, StringIO
from functools import lru_cache
from zensols.util import APIError


class ConfigurationError(APIError):
    pass


@lru_cache(maxsize=50)
def _get_str_space(n_spaces: int) -> str:
    return ' ' * n_spaces


class Writable(ABC):
    """An interface for classes that have multi-line debuging capability.

    .. document private functions
    .. automethod:: _trunc
    .. automethod:: _sp
    .. automethod:: _set_indent
    .. automethod:: _write_line
    .. automethod:: _write_block
    .. automethod:: _write_object
    .. automethod:: _write_iterable
    .. automethod:: _write_dict

    """
    WRITABLE_INDENT_SPACE = 4
    WRITABLE_MAX_COL = 80

    @classmethod
    def _trunc(cls, s: str, max_len: int = None) -> str:
        max_len = cls.WRITABLE_MAX_COL if max_len is None else max_len
        sl = len(s)
        if sl >= max_len:
            ml = max_len - 3
            s = s[:ml] + '...'
        return s

    def _sp(self, depth: int):
        """Utility method to create a space string.

        """
        indent = getattr(self, '_indent', None)
        indent = self.WRITABLE_INDENT_SPACE if indent is None else indent
        return _get_str_space(depth * indent)

    def _set_indent(self, indent: int = None):
        """Set the indentation for the instance.  By default, this value is 4.

        :param indent: the value to set as the indent for this instance, or
                       ``None`` to unset it

        """
        self._indent = indent
        _get_str_space.cache_clear()

    def _write_empty(self, writer: TextIOBase):
        """Write an empty line.

        """
        writer.write('\n')

    def _write_line(self, line: str, depth: int, writer: TextIOBase,
                    max_len: Union[bool, int] = False):
        """Write a line of text ``line`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        s = f'{self._sp(depth)}{line}'
        if max_len is True:
            s = self._trunc(s)
        elif max_len is False:
            pass
        elif isinstance(max_len, int):
            s = self._trunc(s, max_len)
        else:
            raise ConfigurationError(
                'Max_len must either be a boolean or integer')
        writer.write(s)
        self._write_empty(writer)

    def _write_divider(self, depth: int, writer: TextIOBase, char: str = '-',
                       width: int = None):
        """Write a text based dividing line (like <hr></hr> in html).

        """
        width = self.WRITABLE_MAX_COL if width is None else width
        width = width - (depth * self.WRITABLE_INDENT_SPACE)
        line = self._sp(depth) + (char * width)
        writer.write(line)
        self._write_empty(writer)

    def _write_block(self, lines: str, depth: int, writer: TextIOBase,
                     limit: int = None):
        """Write a block of text with indentation.

        """
        sp = self._sp(depth)
        lines = lines.split('\n')
        if limit is not None:
            lines = it.islice(lines, limit)
        for line in lines:
            writer.write(sp)
            writer.write(line)
            self._write_empty(writer)

    def _write_object(self, obj: Any, depth: int, writer: TextIOBase):
        """Write an object based on the class of the instance.

        """
        if isinstance(obj, dict):
            self._write_dict(obj, depth, writer)
        elif isinstance(obj, (list, tuple, set)):
            self._write_iterable(obj, depth, writer)
        elif isinstance(obj, WRITABLE_CLASS):
            obj.write(depth, writer)
        else:
            self._write_line(str(obj), depth, writer)

    def _write_key_value(self, k: Any, v: Any, depth: int, writer: TextIOBase):
        """Write a key value pair from a dictionary.

        """
        sp = self._sp(depth)
        writer.write(f'{sp}{k}: {v}\n')

    def _write_iterable(self, data: Iterable[Any], depth: int,
                        writer: TextIOBase, include_index: bool = False):
        """Write list ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        :param include_index: if ``True``, add an incrementing index for each
                              element in the output

        """
        for i, v in enumerate(data):
            if include_index:
                self._write_line(f'i: {i}', depth, writer)
            self._write_object(v, depth + (1 if include_index else 0), writer)

    def _is_container(self, v: Any) -> bool:
        """Return whether or not ``v`` is a container object: ``dict``, ``list``,
        ``tuple`` or a this class.

        """
        return isinstance(v, (dict, list, tuple, WRITABLE_CLASS))

    def _write_dict(self, data: dict, depth: int, writer: TextIOBase,
                    inline: bool = False):
        """Write dictionary ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        sp = self._sp(depth)
        keys = data.keys()
        if not isinstance(data, OrderedDict):
            keys = sorted(keys)
        for k in keys:
            v = data[k]
            if not inline and self._is_container(v):
                writer.write(f'{sp}{k}:\n')
                self._write_object(v, depth + 1, writer)
            else:
                self._write_key_value(k, v, depth, writer)

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention ``depth``.

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        """
        pass

    def write_to_log(self, logger: Logger, level: int = logging.INFO,
                     depth: int = 0, split_lines: bool = True):
        """Just like :meth:`write` but write the content to a log message.

        :param logger: the logger to write the message containing content of
                       this writable

        :param level: the logging level given in the :mod:`logging` module

        :param depth: the starting indentation depth

        :param split_lines: if ``True`` each line is logged separately

        """
        sio = StringIO()
        self.write(depth, sio)
        lines = (sio.getvalue(),)
        if split_lines:
            lines = lines[0].strip().split('\n')
        for line in lines:
            logger.log(level, line)


WRITABLE_CLASS = Writable
