import unittest
import io
import builtins
import traceback
from functools import wraps
import sys
from pathlib import Path
from io import StringIO
from zensols.util import FileLikeType, openread


def opener(old_open):
    @wraps(old_open)
    def tracking_open(*args, **kw):
        file = old_open(*args, **kw)

        old_close = file.close

        @wraps(old_close)
        def close():
            old_close()
            open_files.remove(file)
        file.close = close
        file.stack = traceback.extract_stack()

        open_files.add(file)
        return file
    return tracking_open


# track open files to explicitly control and assert when files are left open
open_files = set()
io.open = opener(io.open)
builtins.open = opener(builtins.open)


class TestDirectoryCompStash(unittest.TestCase):
    FILE_PATH = 'test-resources/config-test.conf'

    def _get_should_content(self) -> str:
        with open(self.FILE_PATH) as f:
            return f.read()

    def test_type(self):
        from_inst = FileLikeType.from_instance
        self.assertEqual(FileLikeType.filelike, from_inst(StringIO()))
        with open(self.FILE_PATH) as f:
            self.assertEqual(FileLikeType.filelike, from_inst(f))
        self.assertEqual(FileLikeType.path, from_inst(Path('nada')))
        self.assertEqual(FileLikeType.string_path, from_inst(self.FILE_PATH))
        self.assertEqual(FileLikeType.none, from_inst(1))
        self.assertEqual(FileLikeType.none, from_inst(None))
        self.assertEqual(FileLikeType.none, from_inst('nada'))
        self.assertEqual(FileLikeType.stdin, from_inst(sys.stdin))
        self.assertEqual(FileLikeType.stdin, from_inst('-'))
        self.assertEqual(FileLikeType.stdin, from_inst(Path('-')))

    def test_type_readable(self):
        self.assertTrue(FileLikeType.filelike.is_readable)
        self.assertTrue(FileLikeType.path.is_readable)
        self.assertTrue(FileLikeType.stdin.is_readable)
        self.assertFalse(FileLikeType.none.is_readable)

    def test_instance_readable(self):
        def is_readable(o) -> bool:
            ftype = FileLikeType.from_instance(o)
            return ftype.is_readable

        self.assertTrue(is_readable(StringIO()))
        with open(self.FILE_PATH) as f:
            self.assertTrue(is_readable(f))
        self.assertTrue(is_readable(Path('nada')))
        self.assertTrue(is_readable(self.FILE_PATH))
        self.assertFalse(is_readable(1))
        self.assertFalse(is_readable(None))
        self.assertFalse(is_readable('nada'))
        self.assertTrue(is_readable(sys.stdin))

    def test_read(self):
        # let the unittest warn on unclosed files
        should: str = self._get_should_content()
        fd = open(self.FILE_PATH)
        with openread(fd) as f:
            self.assertEqual(should, f.read())
        self.assertFalse(fd.closed)
        fd.close()
        with openread(Path(self.FILE_PATH)) as f:
            self.assertEqual(should, f.read())
        with openread(self.FILE_PATH) as f:
            self.assertEqual(should, f.read())
        self.assertEqual(set(), open_files, 'file(s) were not closed')

    def test_stdin_read(self):
        with openread(sys.stdin) as f:
            self.assertEqual(id(sys.stdin), id(f))
        with openread('-') as f:
            self.assertEqual(id(sys.stdin), id(f))
        with openread(Path('-')) as f:
            self.assertEqual(id(sys.stdin), id(f))

    def test_no_close_stdin(self):
        with openread(sys.stdin):
            pass
        self.assertFalse(sys.stdin.closed)

    def test_no_close(self):
        # let the unittest warn on unclosed files
        try:
            with openread(self.FILE_PATH, no_close=True):
                pass
            self.assertEqual(1, len(open_files))
        finally:
            for f in tuple(open_files):
                f.close()
            open_files.clear()

    def test_non_file(self):
        with self.assertRaisesRegex(OSError, '^Not openable: nada'):
            with openread('nada') as f:
                print(f)
        with openread('nada', raise_error=False) as f:
            self.assertEqual(None, f)
