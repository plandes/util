import unittest
from time import sleep
from zensols.util.time import time, timeout, timeprotect, TimeoutError


class TestTime(unittest.TestCase):
    def test_timeout_func(self):
        @timeout(1)
        def sleep_function(s):
            sleep(s)

        sleep_function(.5)

        with self.assertRaises(TimeoutError):
            sleep_function(1.5)

    def test_timeout_class(self):
        class ClientClass(object):
            def __init__(self, s):
                self.s = s

            @timeout(1)
            def sleep_method(self):
                sleep(self.s)

        client = ClientClass(.5)
        client.sleep_method()

        client = ClientClass(1.5)
        with self.assertRaises(TimeoutError):
            client.sleep_method()

    def test_timeprotect(self):
        state = [0]

        with timeprotect(1):
            sleep(.5)
        self.assertEqual(0, state[0])

        with timeprotect(1):
            sleep(1.5)
        self.assertEqual(0, state[0])

        def tofn(tp):
            tp.context[0] = 1

        with timeprotect(1, tofn, state):
            sleep(1.5)

        self.assertEqual(1, state[0])

    def _test_with_time(self, newval, doret):
        v = 1
        with time('log msg with {inner_var}'):
            inner_var = 1
            v = newval
            if doret:
                return (newval, doret)
        self.assertEqual(v, newval)

    def test_with_time(self):
        self.assertEqual(None, self._test_with_time(1, False))
        self.assertEqual((2, True), self._test_with_time(2, True))
        self.assertEqual(('s', True), self._test_with_time('s', True))
