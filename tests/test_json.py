import unittest
from pathlib import Path
from zensols.config import JsonConfig


class testJsonConfig(unittest.TestCase):
    def test_config(self):
        conf = JsonConfig('test-resources/test.json')
        should = set('jsec_1 jsec_2'.split())
        self.assertEqual(should, set(conf.sections))
        self.assertEqual('blue', conf.get_option('jkey1', 'jsec_1'))

    def test_eval(self):
        conf = JsonConfig('test-resources/test.json')
        params = conf.populate(section='jsec_2')
        self.assertTrue(hasattr(params, 'apath'))
        path = params.apath
        self.assertTrue(isinstance(path, Path))
        self.assertTrue('test-resources/test.json', str(path))

    def test_one_level(self):
        conf = JsonConfig('test-resources/test-one-level.json')
        self.assertEqual(set('default'.split()), set(conf.sections))
        self.assertEqual('one level', conf.get_option('param1'))
        self.assertEqual('really simple', conf.get_option('p2'))
