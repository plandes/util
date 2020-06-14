from dataclasses import dataclass
import unittest
import logging
import collections
from zensols.config import Config, ImportConfigFactory, Writeback

logger = logging.getLogger(__name__)


@dataclass
class Temp1(Writeback):
    aval: int


class TestConfigWriteBase(unittest.TestCase):
    def setUp(self):
        self.config = Config('test-resources/config-write.conf')
        self.factory = ImportConfigFactory(self.config)


class TestConfigWrite(TestConfigWriteBase):
    def test_primitive(self):
        config = self.config
        sec = config.get_options('temp1')
        self.assertEqual({'aval': '1', 'class_name': 'test_config_write.Temp1'}, sec)

        empty_sec = 'empty'
        sec = config.get_options(empty_sec)
        self.assertEqual({}, sec)
        config.set_option('aval', 'astr', empty_sec)
        sec = config.get_options(empty_sec)
        should = {'aval': 'astr'}
        self.assertEqual(sec, should)

        for i, obj in enumerate([True, 1.23, 23, 'abc']):
            k = f'val{i}'
            should[k] = str(obj)
            config.set_option(k, obj, empty_sec)
            sec = config.get_options(empty_sec)
            self.assertEqual(sec, should)

        data = collections.OrderedDict({'k1': 1.23, 'k2': [3, 2, 0]})
        config.set_option('j1', data, empty_sec)
        should['j1'] = 'json: {"k1": 1.23, "k2": [3, 2, 0]}'
        sec = config.get_options(empty_sec)
        self.assertEqual(sec, should)


class TestConfigWriteBack(TestConfigWriteBase):
    def test_write(self):
        t1 = self.factory('temp1')
        self.assertTrue(isinstance(t1, Temp1))
        self.assertEqual(1, t1.aval)
        t1.aval = 5
        self.assertEqual(5, t1.aval)
        self.assertEqual('5', self.config.get_option('aval', section='temp1'))
