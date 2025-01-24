"""General utility classes to measuring time it takes to do work, to logging
and fork/exec operations.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Any, Type
from dataclasses import dataclass, field
import sys
import traceback
from collections import OrderedDict
from io import StringIO, TextIOBase
from . import Writable


class APIError(Exception):
    """Base exception from which almost all library raised errors extend.

    """
    pass


@dataclass
class Failure(Writable):
    """Contains information for failures as caught exceptions used by
    programatic methods.

    """
    exception: Exception = field(default=None)
    """The exception that was generated."""

    thrower: Any = field(default=None)
    """The instance of the class that is throwing the exception."""

    traceback: traceback = field(default=None, repr=False)
    """The stack trace."""

    message: str = field(default=None)
    """A high level explaination of what went wrong"""

    def __post_init__(self):
        self._exc_info: Tuple[Type[Exception], Exception, traceback] = \
            sys.exc_info()
        if self.exception is None:
            self.exception: Exception = self._exc_info[1]
        if self.traceback is None:
            self.traceback: traceback = self._exc_info[2]
        self._traceback_str: str = None

    def _print_stack(self, writer: TextIOBase = sys.stdout):
        """Print the stack trace of the exception that caused the failure."""
        traceback.print_exception(*self._exc_info, file=writer)

    @property
    def traceback_str(self) -> str:
        """The stack trace as a string.

        :see :meth:`print_stack`

        """
        if self._traceback_str is None:
            sio = StringIO()
            self._print_stack(writer=sio)
            self._traceback_str = sio.getvalue()
        return self._traceback_str

    def print_stack(self, writer: TextIOBase = sys.stdout):
        """Print the stack trace of the exception that caused the failure."""
        writer.write(self.traceback_str)

    def rethrow(self):
        """Raises :obj:`exception`."""
        raise self.exception

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention
        ``depth``.

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        """
        message: str = self.message
        if message is None or len(self.message) == 0:
            message = str(self.exception)
            if len(message) == 0:
                message = f'Exception: {type(self.exception)}'
        self._write_line(f'{message}:', depth, writer)
        self._write_block(self.traceback_str, depth + 1, writer)

    def asdict(self) -> Dict[str, Any]:
        """Return the content of the object as a dictionary."""
        return OrderedDict(
            [['message', self.message],
             ['exception', self.exception],
             ['trace', self.traceback_str]])

    def __getstate__(self) -> Dict[str, Any]:
        self.traceback_str
        state = self.__dict__
        state['thrower'] = None
        state['traceback'] = None
        state['_exc_info'] = None
        return state

    def __setstate__(self, state: Dict[str, Any]):
        self.__dict__ = state

    def __str__(self) -> str:
        msg: str = str(self.exception) if self.message is None else self.message
        return 'no information' if msg is None else msg

    def __repr__(self) -> str:
        msg: str = str(self)
        return str(f'{type(self.exception).__name__}: {msg}')
