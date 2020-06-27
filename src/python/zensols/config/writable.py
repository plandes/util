"""A class that allows human readable information (sometimes debugging) output
with a hierarchical structure.

"""
__author__ = 'Paul Landes'

from typing import Union
from abc import ABC, abstractmethod
import sys
from io import TextIOWrapper
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
                    writer: TextIOWrapper = sys.stdout,
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

    def _write_dict(self, data: dict, depth: int = 0,
                    writer: TextIOWrapper = sys.stdout):
        """Write dictionary ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        sp = self._sp(depth)
        for k in sorted(data.keys()):
            v = data[k]
            if isinstance(v, dict):
                writer.write(f'{sp}{k}:\n')
                self._write_dict(v, depth + 1, writer)
            else:
                writer.write(f'{sp}{k}: {v}\n')

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention ``depth``.

        """
        pass
