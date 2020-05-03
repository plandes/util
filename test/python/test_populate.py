import unittest
import logging
from pathlib import Path
from zensols.config import Config

logger = logging.getLogger(__name__)


class TestConfigPopulate(unittest.TestCase):
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

    def test_eval(self):
        s = self.conf.populate()
        self.assertEqual(dict, type(s.param9))
        self.assertEqual(s.param9, {'scott': 2, 'paul': 1})
        self.assertEqual(list, type(s.param10))
        self.assertEqual(s.param10, [1, 5, 10])

    def test_path(self):
        s = self.conf.populate()
        self.assertTrue(isinstance(s.param11, Path))
        self.assertEqual('/tmp/some/file.txt', str(s.param11.absolute()))

    def test_by_section(self):
        s = self.conf.populate({}, section='single_section')
        self.assertEqual({'car': 'bmw', 'animal': 'dog'}, s)

    def test_eval_import(self):
        s = self.conf.populate({}, section='eval_test')
        counts = tuple(range(3))
        self.assertEqual({'car': 'bmw', 'animal': 'dog', 'counts': counts}, s)
