"""General utility classes to measuring time it takes to do work, to logging
and fork/exec operations.

"""
__author__ = 'Paul Landes'

import sys
from typing import Any
from dataclasses import dataclass, field
import traceback
from io import TextIOBase


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
    """The insstance of the class that is throwing the exception."""

    traceback: traceback = field(default=None, repr=False)
    """The stack trace."""

    message: str = field(default=None)
    """A high level explaination of what went wrong"""

    def __post_init__(self):
        self._exec_info = sys.exc_info()
        if self.traceback is None:
            self.traceback = self._exec_info[2]

    def print_stack(self, writer: TextIOBase = sys.stdout):
        traceback.print_exception(*self._exec_info, file=writer)

    def __str__(self) -> str:
        msg: str = str(self.exception) if self.message is None else self.message
        return str(f'{type(self.exception).__name__}: {msg}')

    def __repr__(self) -> str:
        return self.__str__()


from .std import *
from .time import *
from .hasher import *
from .log import *
from .executor import *
from .pkgres import *
