"""Classes to generate, track and clean up temporary files.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Tuple, List
import logging
from pathlib import Path
import tempfile as tf

logger = logging.getLogger(__name__)


class TemporaryFileName(object):
    """Create a temporary file names on the file system.  Note that this does not
    create the file object itself, only the file names.  In addition, the
    generated file names are tracked and allow for deletion.  Specified
    directories are also created, which is only needed for non-system temporary
    directories.

    The object is iterable, so usage with ``itertools.islice`` can be used to
    get as many temporary file names as desired.  Calling instances (no
    arguments) generate a single file name.

    """
    def __init__(self, directory: str = None, file_fmt: str = '{name}',
                 create: bool = False, remove: bool = True):
        """Initialize with file system data.

        :param directory: the parent directory of the generated file

        :param file_fmt: a file format that substitutes ``name`` for the create
                         temporary file name; defaults to ``{name}``

        :param create: if ``True``, create ``directory`` if it doesn't exist

        :param remove: if ``True``, remove tracked generated file names if they
                       exist

        :see tempfile:

        """
        if directory is None:
            self._directory = Path(tf._get_default_tempdir())
        else:
            self._directory = Path(directory)
        self._file_fmt = file_fmt
        self._create = create
        self._remove = remove
        self._created: List[Path] = []

    @property
    def files(self) -> Tuple[Path, ...]:
        """Return the file that have been created thus far."""
        return tuple(self._created)

    def __iter__(self) -> TemporaryFileName:
        return self

    def _format_name(self, fname: str) -> str:
        return self._file_fmt.format(name=fname, index=len(self))

    def __next__(self) -> Path:
        fname = next(tf._get_candidate_names())
        fname = self._format_name(fname)
        if self._create and not self._directory.exists():
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'creating directory {self._directory}')
            self._directory.mkdir(parents=True, exist_ok=True)
        path = Path(self._directory, fname)
        self._created.append(path)
        return path

    def __call__(self) -> Path:
        return next(self)

    def __len__(self) -> int:
        return len(self._created)

    def clean(self):
        """Remove any files generated from this instance.  Note this only deletes the
        files, not the parent directory (if it was created).

        This does nothing if ``remove`` is ``False`` in the initializer.

        """
        if self._remove:
            for path in self._created:
                logger.debug(f'delete candidate: {path}')
                if path.exists():
                    logger.info(f'removing temorary file {path}')
                    path.unlink()


class tempfile(object):
    """Generate a temporary file name and return the name in the ``with``
    statement.  Arguments to the form are the same as ``TemporaryFileName``.
    The temporary file is deleted after completion (see ``TemporaryFileName``).

    Example:

    .. code-block:: python

        with tempfile('./tmp', create=True) as fname:
            print(f'writing to {fname}')
            with open(fname, 'w') as f:
                f.write('this file will be deleted, but left with ./tmp\\n')

    """
    def __init__(self, *args, **kwargs):
        self.temp = TemporaryFileName(*args, **kwargs)

    def __enter__(self):
        self.path = self.temp()
        return self.path

    def __exit__(self, type, value, traceback):
        self.temp.clean()
