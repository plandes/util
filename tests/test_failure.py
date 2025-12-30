import pickle
import sys
import traceback
from io import StringIO, BytesIO
from logutil import LogTestCase
from zensols.util import APIError, Failure


class TestArgumentParse(LogTestCase):
    def _raise_ex(self):
        raise APIError('Test error')

    def _get_failure(self, add_error: bool) -> Failure:
        try:
            self._raise_ex()
        except APIError as e:
            if add_error:
                return Failure(e)
            else:
                return Failure()

    def _test_failure(self, add_error: bool):
        fail: Failure = self._get_failure(add_error)
        self.assertEqual(Failure, type(fail))
        self.assertEqual('Test error', str(fail))
        self.assertEqual('APIError: Test error', repr(fail))
        self.assertTrue(fail.traceback_str.startswith(
            'Traceback (most recent call last):'))
        should = 8 if sys.version_info.minor > 12 else 7
        self.assertEqual(should, len(fail.traceback_str.split('\n')))

    def test_raise(self):
        with self.assertRaisesRegex(APIError, r'^Test error.*'):
            self._raise_ex()

    def test_failure(self):
        self._test_failure(True)
        self._test_failure(False)

    def test_failure_rethrow(self):
        fail: Failure = self._get_failure(False)
        ftrace: str
        try:
            fail.rethrow()
        except APIError:
            sio = StringIO()
            traceback.print_exception(*sys.exc_info(), file=sio)
            ftrace = sio.getvalue()
        self.assertTrue(ftrace.startswith('Traceback (most recent call last):'))
        should = 13 if sys.version_info.minor > 12 else 11
        self.assertEqual(should, len(ftrace.split('\n')))
        with self.assertRaisesRegex(APIError, r'^Test error.*'):
            fail.rethrow()

    def test_failure_pickle(self):
        fail: Failure = self._get_failure(False)
        sio = StringIO()
        fail.write(writer=sio)
        fwrite: str = sio.getvalue()

        bio = BytesIO()
        pickle.dump(fail, bio)
        bio.seek(0)
        pfail: Failure = pickle.load(bio)

        self.assertEqual(str(fail), str(pfail))
        self.assertEqual(fail.traceback_str, pfail.traceback_str)

        sio = StringIO()
        fail.write(writer=sio)
        pfwrite: str = sio.getvalue()
        self.assertEqual(fwrite, pfwrite)
