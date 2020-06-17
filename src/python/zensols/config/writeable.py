from abc import ABC, abstractmethod
import sys
from io import TextIOWrapper


class Writable(ABC):
    """An interface for classes that have multi-line debuging capability.

    """
    def _sp(self, depth: int):
        """Utility method to create a space string.

        """
        indent = getattr(self, '_indent', 4)
        return ' ' * (depth * indent)

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
        for k, v in data.items():
            writer.write(f'{sp}{k}: {v}\n')

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention ``depth``.

        """
        pass
