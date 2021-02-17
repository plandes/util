import unittest
from pathlib import Path
from zensols.config import ImportIniConfig


class TestImportConfig(unittest.TestCase):
    def test_config(self):
        conf = ImportIniConfig('test-resources/import-config-test.conf')
        should = set(('config default empty import_ini1 import_str2 ' +
                      'import_a_json sec1 sec2 sec3 sec4 temp1 temp2 grk ' +
                      'jsec_1 jsec_2').split())
        self.assertEqual(should, set(conf.sections))
        self.assertEqual('this is a cool test', conf.get_option('text', 'sec1'))
        self.assertEqual('imported firstval', conf.get_option('text', 'sec2'))
        self.assertEqual('local import of a greek letter', conf.get_option('text', 'sec3'))
        self.assertEqual('path: test-resources/test.json', conf.get_option('text', 'sec4'))
        jconf = conf.populate(section='sec4')
        path = jconf.text
        self.assertTrue(isinstance(path, Path))
