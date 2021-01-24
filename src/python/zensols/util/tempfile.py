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
            self.directory = Path(tf._get_default_tempdir())
        else:
            self.directory = Path(directory)
        self.file_fmt = file_fmt
        self.create = create
        self.remove = remove
        self.created = []

    def __iter__(self):
        return self

    def __next__(self):
        fname = next(tf._get_candidate_names())
        fname = self.file_fmt.format(**{'name': fname})
        if self.create and not self.directory.exists():
            logger.info(f'creating directory {self.directory}')
            self.directory.mkdir(parents=True, exist_ok=True)
        path = Path(self.directory, fname)
        self.created.append(path)
        return path

    def __call__(self):
        return next(self)

    def clean(self):
        """Remove any files generated from this instance.  Note this only deletes the
        files, not the parent directory (if it was created).

        This does nothing if ``remove`` is ``False`` in the initializer.

        """
        if self.remove:
            for path in self.created:
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
