import unittest
import logging
from configparser import NoSectionError
from zensols.config import IniConfig

logger = logging.getLogger(__name__)


class TestConfig(unittest.TestCase):
    def test_config(self):
        conf = IniConfig('test-resources/config-test.conf')
        self.assertEqual({'param1': '3.14'}, conf.options)

    def test_config_single_opt(self):
        conf = IniConfig('test-resources/config-test.conf')
        self.assertEqual('3.14', conf.get_option('param1'))

    def test_missing_default_raises_error(self):
        def run_conf_create():
            conf = IniConfig('test-resources/config-test-nodef.conf')
            opts = conf.options

        self.assertRaises(NoSectionError, run_conf_create)

    def test_no_default(self):
        conf = IniConfig('test-resources/config-test-nodef.conf', robust=True)
        self.assertEqual({}, conf.options)

    def test_print(self):
        conf = IniConfig('test-resources/config-test.conf')
        s = str(conf)
        self.assertEqual("file: test-resources/config-test.conf, section: {'default'}", s)

    def test_list_parse(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        self.assertEqual(['one', 'two', 'three'],
                         conf.get_option_list('param1'))
        self.assertEqual(True, conf.get_option_boolean('param2'))
        self.assertEqual(True, conf.get_option_boolean('param3'))
        self.assertEqual(True, conf.get_option_boolean('param4'))
        self.assertEqual(False, conf.get_option_boolean('param5'))
        self.assertEqual(False, conf.get_option_boolean('no_such_param'))
        self.assertEqual([], conf.get_option_list('no_such_param'))

    def test_has_option(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        self.assertTrue(conf.has_option('param1'))
        self.assertTrue(conf.has_option('param1', section='default'))
        self.assertFalse(conf.has_option('param1', section='NOSEC'))
        self.assertFalse(conf.has_option('NOPARARM'))
