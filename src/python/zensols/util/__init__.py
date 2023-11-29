"""General utility classes to measuring time it takes to do work, to logging
and fork/exec operations.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any
from dataclasses import dataclass, field
import sys
import traceback
from collections import OrderedDict
from io import StringIO, TextIOBase


class APIError(Exception):
    """Base exception from which almost all library raised errors extend.

    """
    pass


@dataclass
class Failure(object):
    """Contains information for failures as caught exceptions used by
    programatic methods.

    """
    exception: Exception = field()
    """The exception that was generated."""

    thrower: Any = field(default=None)
    """The instance of the class that is throwing the exception."""

    traceback: traceback = field(default=None, repr=False)
    """The stack trace."""

    message: str = field(default=None)
    """A high level explaination of what went wrong"""

    def __post_init__(self):
        self._exec_info = sys.exc_info()
        if self.traceback is None:
            self.traceback = self._exec_info[2]

    def print_stack(self, writer: TextIOBase = sys.stdout):
        """Print the stack trace of the exception that caused the failure."""
        traceback.print_exception(*self._exec_info, file=writer)

    @property
    def traceback_str(self) -> str:
        """The stack trace as a string.

        :see :meth:`print_stack`

        """
        sio = StringIO()
        self.print_stack(writer=sio)
        return sio.getvalue()

    def rethrow(self):
        """Raises :obj:`exception`."""
        raise self.exception

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention
        ``depth``.

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        """
        sp = ' ' * (2 * depth)
        writer.write(f'{sp}{self.message}:\n')
        self.print_stack(writer)

    def asdict(self) -> Dict[str, Any]:
        """Return the content of the object as a dictionary."""
        return OrderedDict(
            [['message', self.message],
             ['exception', self.exception],
             ['trace', self.traceback_str]])

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__
        del state['thrower']
        return state

    def __setstate__(self, state: Dict[str, Any]):
        self.__dict__ = state

    def __str__(self) -> str:
        msg: str = str(self.exception) if self.message is None else self.message
        return str(f'{type(self.exception).__name__}: {msg}')


from .std import *
from .time import *
from .hasher import *
from .log import *
from .executor import *
from .pkgres import *
