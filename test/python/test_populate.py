import logging
import unittest
from zensols.config import Config

logger = logging.getLogger(__name__)


class TestPersistWork(unittest.TestCase):
    def setUp(self):
        self.conf = Config('test-resources/populate-test.conf')

    def test_primitive(self):
        s = self.conf.populate()
        self.assertEqual(s.param1, 3.14)
        self.assertEqual(s.param2, 9)
        self.assertEqual(s.param3, 10.1)
        self.assertEqual(s.param4, -10.1)
        self.assertEqual(s.param5, 'dog')
        self.assertEqual(s.param6, True)
        self.assertEqual(s.param7, False)
        self.assertEqual(s.param8, None)

    def test_populate(self):
        s = self.conf.populate()
        self.assertEqual(dict, type(s.param9))
        self.assertEqual(s.param9, {'scott': 2, 'paul': 1})
