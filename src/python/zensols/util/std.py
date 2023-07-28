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

    Example::

        with stdout(Path('out.txt')) as f:
            f.write('test')

    """
    STANDARD_OUT_PATH: ClassVar[str] = '-'
    """The string used to indicate to write to standard out."""

    def __init__(self, path: Union[str, Path] = None, extension: str = None,
                 logger: logging.Logger = logger, capture: bool = False,
                 open_args: str = 'w'):
        """Initailize where to write.  If the path is ``None`` or its name is
        :obj:`STANDARD_OUT_PATH`, then standard out is used instead of opening a
        file.

        :param path: the path to write, or ``None``

        :param extension: the extension (sans leading dot ``.``) to postpend to
                          the path if one is not provied in the file name

        :param logger: used to log the successful output of the file, which
                       defaults to this module's logger

        :param capture: whether to redirect standard out (:obj:`sys.stdout`) to
                        the file provided by ``path`` if not already indicated
                        to be standard out

        :param open_args: the arguments given to :func:`open`, which defaults to
                          ``w`` if none are given

        """
        path = Path(path) if isinstance(path, str) else path
        if path is None or path.name == self.STANDARD_OUT_PATH:
            self._path: Path = None
            self._args: str = None
        else:
            if len(path.suffix) == 0 and extension is not None:
                path = path.parent / f'{path.name}.{extension}'
            self._path: Path = path
            self._args: str = open_args
        self._logger: logging.Logger = logger
        self._capture: bool = capture

    def __enter__(self):
        if self._path is None:
            self._sink = sys.stdout
        else:
            self._sink = open(self._path, self._args)
            if self._capture:
                self._stdwrite = stdwrite(self._sink)
                self._stdwrite.__enter__()
        return self._sink

    def __exit__(self, type, value, traceback):
        self._sink.flush()
        logged: bool = False
        if self._sink != sys.stdout:
            try:
                self._sink.close()
                logged = value is None and \
                    self._logger.isEnabledFor(logging.INFO) and \
                    self._path is not None
            except Exception as e:
                logger.error(f'Can not close stream: {e}', e)
        if self._capture:
            self._stdwrite.__exit__(None, None, None)
        if logged:
            self._logger.info(f'wrote: {self._path}')
