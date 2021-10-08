from typing import Sequence
import unittest
import logging


class LogUtil(object):
    @staticmethod
    def reset():
        root = logging.getLogger()
        tuple(map(root.removeHandler, root.handlers[:]))
        tuple(map(root.removeFilter, root.filters[:]))


class LogTestCase(unittest.TestCase):
    def setUp(self):
        LogUtil.reset()

    def tearDown(self):
        LogUtil.reset()

    def config_logging(self, *names: Sequence[str]):
        logging.basicConfig(level=logging.ERROR)
        for lv in names:
            logging.getLogger(lv).setLevel(logging.DEBUG)
