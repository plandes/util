"""Utility classes for system based functionality.

"""
__author__ = 'Paul Landes'

from typing import ClassVar, Union
import logging
from pathlib import Path
from io import TextIOBase
import sys

logger = logging.getLogger(__name__)


class stdwrite(object):
    """Capture standard out/error.

    """
    def __init__(self, stdout: TextIOBase = None, stderr: TextIOBase = None):
        """Initialize.

        :param stdout: the data sink for stdout (i.e. :class:`io.StringIO`)

        :param stdout: the data sink for stderr

        """
        self._stdout = stdout
        self._stderr = stderr

    def __enter__(self):
        self._sys_stdout = sys.stdout
        self._sys_stderr = sys.stderr
        if self._stdout is not None:
            sys.stdout = self._stdout
        if self._stderr is not None:
            sys.stderr = self._stderr

    def __exit__(self, type, value, traceback):
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = self._sys_stdout
        sys.stderr = self._sys_stderr


class stdout(object):
    """Write to a file or standard out.  Arguments are the same as :func:`open`,
    but standard out is used depending on the provided path.

    """
    STANDARD_OUT_PATH: ClassVar[str] = '-'

    def __init__(self, path: Union[str, Path], *args):
        """Initailize where to write.  If the path is ``None`` or its name is
        :obj:`STANDARD_OUT_PATH`, then standard out is used instead of opening a
        file.

        :param path: the path to write, or ``None``

        :param args: the arguments given to :func:`open`

        """
        path = Path(path) if isinstance(path, str) else path
        if path is None or path.name == self.STANDARD_OUT_PATH:
            self._path = None
            self._args = None
        else:
            self._path = path
            self._args = args

    def __enter__(self):
        if self._path is None:
            self._sink = sys.stdout
        else:
            self._sink = open(self._path, *self._args)
        return self._sink

    def __exit__(self, type, value, traceback):
        self._sink.flush()
        if self._sink != sys.stdout:
            try:
                self._sink.close()
            except Exception as e:
                logger.error(f'Can not close stream: {e}', e)
