import unittest
from pathlib import Path
import os
from zensols.config import ImportIniConfig


class TestImportConfig(unittest.TestCase):
    def setUp(self):
        self.conf = ImportIniConfig('test-resources/import-config-test.conf')

    def test_config(self):
        conf = self.conf
        should = set(('config default empty import_ini1 import_str2 ' +
                      'import_a_json sec1 sec2 sec3 sec4 temp1 temp2 grk ' +
                      'jsec_1 jsec_2 imp_env ev').split())
        self.assertEqual(should, set(conf.sections))
        self.assertEqual('this is a cool test', conf.get_option('text', 'sec1'))
        self.assertEqual('imported firstval', conf.get_option('text', 'sec2'))
        self.assertEqual('local import of a greek letter', conf.get_option('text', 'sec3'))
        self.assertEqual('path: test-resources/test.json', conf.get_option('text', 'sec4'))
        jconf = conf.populate(section='sec4')
        path = jconf.text
        self.assertTrue(isinstance(path, Path))

    def test_env(self):
        conf = self.conf
        key = 'unittest.test_impconfig_val'
        testval = 'testval'
        os.environ[key] = testval
        self.assertEqual(testval, conf.get_option(key, 'ev'))
