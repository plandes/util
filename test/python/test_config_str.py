import unittest
from zensols.config import StringConfig, IniConfig


class TestConfigStr(unittest.TestCase):
    def test_singleton_def_section(self):
        conf_str = 'param1=3.14'
        conf = StringConfig(conf_str)
        self.assertEqual({'param1': '3.14'},
                         conf.get_options(section='default'))
        self.assertEqual({'default'}, conf.sections)

    def test_singleton_with_section(self):
        conf_str = 'sec1.param1=3.14'
        conf = StringConfig(conf_str)
        self.assertEqual({'param1': '3.14'}, conf.get_options(section='sec1'))
        self.assertEqual({'sec1'}, conf.sections)

    def test_def_section(self):
        conf_str = 'param1=3.14,param2=cool'
        conf = StringConfig(conf_str)
        self.assertEqual({'param1': '3.14', 'param2': 'cool'},
                         conf.get_options())
        self.assertEqual({'default'}, conf.sections)

    def test_section(self):
        conf_str = 'sec1.param1=3.14,sec1.param2=cool'
        conf = StringConfig(conf_str)
        self.assertEqual({'param1': '3.14', 'param2': 'cool'},
                         conf.get_options(section='sec1'))
        self.assertEqual({'sec1'}, conf.sections)

    def test_sections(self):
        conf_str = 'sec1.param1=3.14,sec2.param2=cool'
        conf = StringConfig(conf_str)
        self.assertEqual({'param1': '3.14'}, conf.get_options(section='sec1'))
        self.assertEqual({'param2': 'cool'}, conf.get_options(section='sec2'))
        self.assertEqual({'sec1', 'sec2'}, conf.sections)

    def test_merge(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        conf_str = 'param1=newval,param2=p2'
        override = StringConfig(conf_str)
        self.assertEqual('one,two,three', conf.get_option('param1'))
        self.assertEqual('true', conf.get_option('param2'))
        conf.merge(override)
        self.assertEqual('newval', conf.get_option('param1'))
        self.assertEqual('p2', conf.get_option('param2'))
        self.assertEqual('TRUE', conf.get_option('param3'))
        self.assertEqual({'default'}, conf.sections)

    def test_sections_merge(self):
        conf = IniConfig('test-resources/config-test-option.conf')
        conf_str = 'param1=newval,sec1.param2=p2'
        override = StringConfig(conf_str)
        self.assertEqual('one,two,three', conf.get_option('param1'))
        self.assertEqual('true', conf.get_option('param2'))
        conf.merge(override)
        self.assertEqual('newval', conf.get_option('param1'))
        self.assertEqual('true', conf.get_option('param2'))
        self.assertEqual('p2', conf.get_option('param2', 'sec1'))
        self.assertEqual({'default', 'sec1'}, conf.sections)
