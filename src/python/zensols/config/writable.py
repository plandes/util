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
                    writer: TextIOWrapper = sys.stdout):
        """Write a line of text ``line`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        writer.write(f'{self._sp(depth)}{line}\n')

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
