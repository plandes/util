import unittest
from configparser import NoSectionError, DuplicateSectionError
from zensols.config import ConfigurableError, IniConfig


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
            conf.options

        self.assertRaises(ConfigurableError, run_conf_create)

    def test_no_default(self):
        with self.assertRaisesRegex(ConfigurableError, r'No section: \'default'):
            conf = IniConfig('test-resources/config-test-nodef.conf')
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
        with self.assertRaisesRegex(ConfigurableError, '^No option: \'default:no_such_param.*'):
            conf.get_option_boolean('no_such_param')
        with self.assertRaisesRegex(ConfigurableError, '^No option: \'default:no_such_param.*'):
            self.assertEqual([], conf.get_option_list('no_such_param'))

    def test_has_option(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        self.assertTrue(conf.has_option('param1'))
        self.assertTrue(conf.has_option('param1', section='default'))
        self.assertFalse(conf.has_option('param1', section='NOSEC'))
        self.assertFalse(conf.has_option('NOPARARM'))

    def test_merge(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        override = IniConfig('test-resources/config-test.conf')
        self.assertEqual('one,two,three', conf.get_option('param1'))
        self.assertEqual('true', conf.get_option('param2'))
        conf.merge(override)
        self.assertEqual('3.14', conf.get_option('param1'))
        self.assertEqual('true', conf.get_option('param2'))

    def test_reload(self):
        conf = IniConfig('test-resources/config-test.conf')
        self.assertEqual('3.14', conf.get_option('param1'))
        conf.set_option('param1', 'newval')
        self.assertEqual('newval', conf.get_option('param1'))
        conf.reload()
        self.assertEqual('3.14', conf.get_option('param1'))


class TestDirConfig(unittest.TestCase):
    def test_happy_path(self):
        conf = IniConfig('test-resources/dconf/happy')
        self.assertEqual({'default', 'sec1'}, conf.sections)
        self.assertEqual({'param1': '3.14'}, conf.get_options('default'))
        self.assertEqual({'param1': 'p1', 'param2': 'p2'}, conf.get_options('sec1'))

    def test_unhappy_path(self):
        conf = IniConfig('test-resources/dconf/sad')
        self.assertRaises(DuplicateSectionError, lambda: conf.sections)
