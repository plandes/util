import unittest
from pathlib import Path
from zensols.config import JsonConfig


class testJsonConfig(unittest.TestCase):
    def setUp(self):
        self.conf = JsonConfig('test-resources/test.json')

    def test_config(self):
        self.conf = JsonConfig('test-resources/test.json')
        should = set('jsec_1 jsec_2'.split())
        self.assertEqual(should, set(self.conf.sections))
        self.assertEqual('blue', self.conf.get_option('jkey1', 'jsec_1'))

    def test_eval(self):
        params = self.conf.populate(section='jsec_2')
        self.assertTrue(hasattr(params, 'apath'))
        path = params.apath
        self.assertTrue(isinstance(path, Path))
        self.assertTrue('test-resources/test.json', str(path))
