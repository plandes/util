"""A class that allows human readable information (sometimes debugging) output
with a hierarchical structure.

"""
__author__ = 'Paul Landes'

from typing import Union, Any, Iterable
from abc import ABC, abstractmethod
import sys
from io import TextIOBase
from functools import lru_cache


@lru_cache(maxsize=50)
def _get_str_space(n_spaces: int) -> str:
    return ' ' * n_spaces


class Writable(ABC):
    """An interface for classes that have multi-line debuging capability.

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

    def _write_line(self, line: str, depth: int = 0,
                    writer: TextIOBase = sys.stdout,
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
            raise ValueError('max_len must either be a boolean or integer')
        writer.write(s + '\n')

    def _write_block(self, lines: str, depth: int = 0,
                     writer: TextIOBase = sys.stdout):
        sp = self._sp(depth)
        for line in lines.split('\n'):
            writer.write(sp)
            writer.write(line)
            writer.write('\n')

    def _write_object(self, obj: Any, depth: int = 0,
                      writer: TextIOBase = sys.stdout):
        if isinstance(obj, dict):
            self._write_dict(obj, depth, writer)
        elif isinstance(obj, (list, tuple, set)):
            self._write_iterable(obj, depth, writer)
        elif isinstance(obj, WRITABLE_CLASS):
            obj.write(depth, writer)
        else:
            self._write_line(str(obj), depth, writer)

    def _write_iterable(self, data: Iterable[Any], depth: int = 0,
                        writer: TextIOBase = sys.stdout):
        """Write list ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        for v in data:
            self._write_object(v, depth, writer)

    def _write_dict(self, data: dict, depth: int = 0,
                    writer: TextIOBase = sys.stdout):
        """Write dictionary ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        sp = self._sp(depth)
        for k in sorted(data.keys()):
            v = data[k]
            if isinstance(v, (dict, list, tuple, WRITABLE_CLASS)):
                writer.write(f'{sp}{k}:\n')
                self._write_object(v, depth + 1, writer)
            else:
                writer.write(f'{sp}{k}: {v}\n')

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention ``depth``.

        """
        pass


WRITABLE_CLASS = Writable
