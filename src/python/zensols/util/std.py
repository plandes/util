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
    '''Write to a file or standard out.  This is desigend to be used in command
    line application (CLI) applications with the :mod:`zensols.cli` module.
    Application class can pass a :class:`pathlib.Path` to a method with this
    class.

    Example::

        def write(self, output_file: Path = Path('-')):
            """Write data.

            :param output_file: the output file name, ``-`` for standard out, or
                                ``+`` for a default

            """
            with stdout(output_file, recommend_name='unknown-file-name',
                        extension='txt', capture=True, logger=logger):
                print('write data')

    '''
    STANDARD_OUT_PATH: ClassVar[str] = '-'
    """The string used to indicate to write to standard out."""

    FILE_RECOMMEND_NAME: ClassVar[str] = '+'
    """The string used to indicate to use the recommended file name."""

    def __init__(self, path: Union[str, Path] = None, extension: str = None,
                 recommend_name: str = 'unnamed', capture: bool = False,
                 logger: logging.Logger = logger, open_args: str = 'w'):
        """Initailize where to write.  If the path is ``None`` or its name is
        :obj:`STANDARD_OUT_PATH`, then standard out is used instead of opening a
        file.  If ``path`` is set to :obj:`FILE_RECOMMEND_NAME`, it is
        constructed from ``recommend_name``.  If no suffix (file extension) is
        provided for ``path`` then ``extesion`` is used if given.

        :param path: the path to write, or ``None``

        :param extension: the extension (sans leading dot ``.``) to postpend to
                          the path if one is not provied in the file name

        :param recommend_name: the name to use as the prefix if ``path`` is not
                               provided

        :param capture: whether to redirect standard out (:obj:`sys.stdout`) to
                        the file provided by ``path`` if not already indicated
                        to be standard out

        :param logger: used to log the successful output of the file, which
                       defaults to this module's logger

        :param open_args: the arguments given to :func:`open`, which defaults to
                          ``w`` if none are given

        """
        path = Path(path) if isinstance(path, str) else path
        if path is None or self.is_stdout(path):
            path = None
        elif (path is not None and
              path.name == self.FILE_RECOMMEND_NAME and
              recommend_name is not None):
            path = Path(recommend_name)
        if path is None:
            self._path = None
            self._args: str = None
        else:
            if len(path.suffix) == 0 and extension is not None:
                path = path.parent / f'{path.name}.{extension}'
            self._path: Path = path
            self._args: str = open_args
        self._logger: logging.Logger = logger
        self._capture: bool = capture
        self._stdwrite: stdwrite = None

    @classmethod
    def is_stdout(self, path: Path) -> bool:
        """Return whether the path indicates to use to standard out."""
        return path.name == self.STANDARD_OUT_PATH

    @classmethod
    def is_file_recommend(self, path: Path) -> bool:
        """Return whether the path indicates to recommmend a file."""
        return path.name == self.FILE_RECOMMEND_NAME

    def __enter__(self):
        if self._path is None:
            self._sink = sys.stdout
            self._should_close = False
        else:
            self._sink = open(self._path, self._args)
            self._should_close = True
            if self._capture:
                self._stdwrite = stdwrite(self._sink)
                self._stdwrite.__enter__()
        return self._sink

    def __exit__(self, type, value, traceback):
        self._sink.flush()
        should_log: bool = False
        if self._should_close:
            try:
                if self._stdwrite is not None:
                    self._stdwrite.__exit__(None, None, None)
                self._sink.close()
                should_log = value is None and \
                    self._logger.isEnabledFor(logging.INFO) and \
                    self._path is not None
            except Exception as e:
                logger.error(f'Can not close stream: {e}', e)
        if should_log:
            self._logger.info(f'wrote: {self._path}')
