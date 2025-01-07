"""Utility classes for system based functionality.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Any, Type, ClassVar, Union
from enum import Enum, auto
import logging
from pathlib import Path
from io import IOBase, TextIOBase, StringIO
import sys

logger = logging.getLogger(__name__)


_STANDARD_IN_OUT_SYMBOL = '-'
"""The string used to indicate to write to standard in."""


class FileLikeType(Enum):
    """Indicates readability aspects of a Python object.  Enumeration values and
    helper methods specify how an object might be readable and in what way.
    This class describes types can be files-like, :class:`pathlib.Path`, strings
    that point to files, and :obj:`sys.stdin`.  The string or path
    :class:`~.stdout.STANDARD_OUT_PATH` is treated as standard in.

    """
    filelike = auto()
    path = auto()
    string_path = auto()
    stdin = auto()
    none = auto()

    @classmethod
    def from_instance(cls: Type, instance: Any) -> FileLikeType:
        """Return an instance of this enumeration based on the type of
        ``instance``.

        """
        fl_type: FileLikeType = cls.none
        is_path: bool = isinstance(instance, Path)
        if is_path and instance.name == _STANDARD_IN_OUT_SYMBOL:
            instance = _STANDARD_IN_OUT_SYMBOL
        if id(instance) == id(sys.stdin) or instance == _STANDARD_IN_OUT_SYMBOL:
            fl_type = cls.stdin
        elif is_path:
            fl_type = cls.path
        elif isinstance(instance, str) and Path(instance).exists():
            fl_type = cls.string_path
        elif isinstance(instance, IOBase):
            fl_type = cls.filelike
        return fl_type

    @staticmethod
    def is_standard_in(instance: Any) -> bool:
        """Whether ``instance`` is not :obj:`sys.stdin` but represents it."""
        if id(instance) == id(sys.stdout) or \
           instance == _STANDARD_IN_OUT_SYMBOL:
            return True
        else:
            is_path: bool = isinstance(instance, Path)
            return is_path and instance.name == _STANDARD_IN_OUT_SYMBOL

    @property
    def is_readable(self) -> bool:
        """Whether the enumeration value can be read."""
        return self.value != self.none.value

    @property
    def is_openable(self) -> bool:
        """Whether an object can be opened with :function:`open`."""
        return self.value == self.path.value or \
            self.value == self.string_path.value


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
    STANDARD_OUT_PATH: ClassVar[str] = _STANDARD_IN_OUT_SYMBOL
    """The string used to indicate to write to standard out."""

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
        if path is not None and self.is_stdout(path):
            path = None
        elif (path is None and recommend_name is not None):
            if extension is not None:
                recommend_name = f'{recommend_name}.{extension}'
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


class openread(object):
    """Open an file object for reading if possible, and close it only if
    necessary.  Input types are described by :class:`.FileLikeType`.  If the
    source is

        * :class:`~pathlib.Path`: read a a file

        * :class:`builtins.str`: read as a file if ``interpret_str`` is
          ``True`` and it points to a file; otherwise, the string is read

        * *file-like object* such as any :class:`~io.IOBase` (sub)class, it is
           read a file

    Example::

        import sys
        import itertools as it

        with openread(sys.stdin) as f:
            line = it.islice(f.readlines(), 1)

    """
    def __init__(self, source: Any, interpret_str: bool = False,
                 raise_error: bool = True, no_close: bool = False,
                 *open_args, **open_kwargs):
        """Initialize.

        :param source: the data source

        :param interpret_str: whether to read the string or use it as a file
                              name

        :param raise_error: if ``True`` raise :class:`~builtins.OSError` if
                            ``source`` is an object that can not be opened or
                            read
        :param no_close: do not close the file object (if opened in the first
                         place), even if it should be

        :param open_kwargs: keyword argument passed to :func:`open`

        """
        self._source = source
        self.file_like_type = FileLikeType.from_instance(source)
        self._interpret_str = interpret_str
        self._raise_error = raise_error
        self._no_close = no_close
        self._open_kwargs = open_kwargs
        self._fd = None

    def __enter__(self):
        if self._interpret_str and \
           isinstance(self._source, str) and \
           not FileLikeType.is_standard_in(self._source):
            self._fd = StringIO(self._source)
            return self._fd
        elif FileLikeType.is_standard_in(self._source):
            self._source = sys.stdin
            return self._source
        elif self.file_like_type.is_openable:
            self._fd = open(self._source, **self._open_kwargs)
            return self._fd
        elif self.file_like_type == self.file_like_type.none:
            if self._raise_error:
                raise OSError(
                    f'Not openable: {self._source} ({type(self._source)})')
            return None
        else:
            return self._source

    def __exit__(self, type, value, traceback):
        if self._fd is not None and not self._no_close:
            self._fd.close()
