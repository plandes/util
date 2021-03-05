"""Utility classes for system based functionality.

"""
__author__ = 'Paul Landes'

from io import TextIOBase
import sys


class stdwrite(object):
    """Capture standard out/error.

    """
    def __init__(self, stdout: TextIOBase = None, stderr: TextIOBase = None):
        """Initialize.

        :param stdout: the data sink for stdout (i.e. :class:`io.StringIO`)

        :param stdout: the data sink for stderr

        """
        self.stdout = stdout
        self.stderr = stderr

    def __enter__(self):
        self._sys_stdout = sys.stdout
        self._sys_stderr = sys.stderr
        if self.stdout is not None:
            sys.stdout = self.stdout
        if self.stderr is not None:
            sys.stderr = self.stderr

    def __exit__(self, type, value, traceback):
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = self._sys_stdout
        sys.stderr = self._sys_stderr
