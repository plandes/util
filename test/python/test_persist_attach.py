import types
import logging
import unittest
from zensols.persist import (
    persisted,
)

logger = logging.getLogger(__name__)


class Temp(object):
    def __init__(self):
        self.n = 0
        self.m = 0

    @persisted('_n')
    def get_n(self):
        self.n += 1
        return self.n

    def get_m(self):
        self.m += 1
        return self.m


class TestPersistAttach(unittest.TestCase):
    def test_attach(self):
        t1 = Temp()
        self.assertEqual(1, t1.get_n())
        self.assertEqual(1, t1.get_n())
        old_get_m = t1.get_m
        t1.get_m = types.MethodType(
            persisted('_m')(lambda s: old_get_m()), t1)
        self.assertEqual(1, t1.get_m())
        self.assertEqual(1, t1.get_m())
