from dataclasses import dataclass
from typing import List, Dict
import unittest
import collections
from zensols.config import (
    IniConfig,
    ImportConfigFactory,
    Writeback,
)
from zensols.persist import PersistableContainer, persisted


@dataclass
class Temp1(Writeback):
    aval: int
    bval: bool
    cval: float
    dval: str
    fval: List[str]
    gval: Dict[str, int]


@dataclass
class Temp2(Writeback, PersistableContainer):
    aval: int

    @property
    @persisted('_propval', transient=True)
    def propval(self):
        return 10


class TestConfigWriteBase(unittest.TestCase):
    def setUp(self):
        self.config = IniConfig('test-resources/config-write.conf')
        self.factory = ImportConfigFactory(self.config)


class TestConfigWrite(TestConfigWriteBase):
    def test_primitive(self):
        config = self.config
        sec = config.get_options('temp1')
        self.assertEqual({'aval': '1',
                          'bval': 'True',
                          'cval': '1.23',
                          'dval': 'firstval',
                          'fval': 'eval: [1, 2]',
                          'gval': "eval: {'a': 3, 'b': 10}",
                          'class_name': 'test_config_write.Temp1'},
                         sec)

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
        opt = self.config.get_option
        t1 = self.factory('temp1')
        self.assertTrue(isinstance(t1, Temp1))
        self.assertEqual(1, t1.aval)
        t1.aval = 5
        self.assertEqual(5, t1.aval)
        self.assertEqual('5', opt('aval', section='temp1'))
        t1.bval = False
        self.assertEqual('False', opt('bval', section='temp1'))
        t1.cval = 12.34
        self.assertEqual('12.34', opt('cval', section='temp1'))
        t1.dval = 'newval'
        self.assertEqual('newval', opt('dval', section='temp1'))
        t1.fval = [6, 7, 8]
        self.assertEqual('json: [6, 7, 8]', opt('fval', section='temp1'))
        t1.gval = collections.OrderedDict({'animal': 'cat', 'car': 'fast'})
        self.assertEqual('json: {"animal": "cat", "car": "fast"}',
                         opt('gval', section='temp1'))

    def test_write_persistable(self):
        t2 = self.factory('temp2')
        self.assertTrue(isinstance(t2, Temp2))
        self.assertEqual(10, t2.propval)
        self.assertEqual(2, t2.aval)
        t2.aval = 5
        self.assertEqual(5, t2.aval)
        self.assertEqual('5', self.config.get_option('aval', section='temp2'))

    def test_write_not_existant(self):
        t1 = self.factory('temp1')
        self.assertTrue(isinstance(t1, Temp1))
        self.assertTrue(self.config.has_option('aval', 'temp1'))
        self.assertEqual(1, t1.aval)
        t1.NOVAL = 5
        self.assertFalse(self.config.has_option('NOVAL', 'temp1'))

    def test_write_object(self):
        t1 = self.factory('temp1')
        self.assertTrue(isinstance(t1, Temp1))
        self.assertTrue(self.config.has_option('aval', 'temp1'))
        self.assertEqual(1, t1.aval)
        should = set([1, 2])
        t1.aval = should
        self.assertEqual('json: {"_type": "set", "_data": [1, 2]}',
                         self.config.get_option('aval', 'temp1'))
        obj = self.config.get_option_object('aval', 'temp1')
        self.assertEqual(should, obj)

    def test_write_instance(self):
        t1 = self.factory('temp1')
        self.assertTrue(isinstance(t1, Temp1))
        self.assertTrue(self.config.has_option('aval', 'temp1'))
        t1.aval = 'instance: temp2'
        self.assertEqual(Temp2, type(t1.aval))
