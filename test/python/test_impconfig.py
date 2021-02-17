import unittest
from pathlib import Path
import os
from zensols.config import ImportIniConfig


class TestImportConfig(unittest.TestCase):
    def setUp(self):
        self.conf = ImportIniConfig('test-resources/import-config-test.conf')
        os.environ['test_impconfig_app_root'] = '.'

    def test_config(self):
        conf = self.conf
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

    def test_child_ref(self):
        self.assertEqual('two way for this: grabbed parents param1, which is cool',
                         self.conf.get_option('text', 'sec5'))

    def test_config_interpolate(self):
        conf = self.conf
        self.assertEqual('test-resources/config-write.conf',
                         conf.get_option('config_file', 'import_ini1'))

    def test_config_sections(self):
        conf = self.conf
        should = set(('import default empty import_ini1 import_str2 ' +
                      'import_a_json sec1 sec2 sec3 sec4 temp1 temp2 grk ' +
                      'jsec_1 jsec_2 imp_env ev impref sec5 need_vars').split())
        self.assertEqual(should, set(conf.sections))
        conf = ImportIniConfig('test-resources/import-config-test.conf',
                               exclude_config_sections=True)
        should = should - set('import import_ini1 import_a_json impref imp_env import_str2'.split())
        self.assertEqual(should, set(conf.sections))
