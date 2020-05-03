from dataclasses import dataclass, field
import types
import logging
import unittest
from zensols.persist import persisted, PersistedWork
from zensols.config import (
    ImportConfigFactory,
    Config,
    RedefinedInjectionError,
)

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Temp(object):
    def __init__(self):
        self.n = 0

    @persisted('_n')
    def get_n(self):
        self.n += 1
        return self.n


@dataclass
class Temp2(object):
    aval: int
    initval: int = field(default=1)


@dataclass
class Temp3(object):
    bval: int = field(default=3)


@dataclass
class Temp4:
    t2: Temp2
    t3: Temp3

@dataclass
class Temp7:
    t2: Temp2
    t3: Temp3


class TestPersistAttach(unittest.TestCase):
    def setUp(self):
        self.conf = Config('test-resources/test-persist-attach.conf')
        self.fac = ImportConfigFactory(self.conf)

    def test_attach(self):
        t1 = Temp()
        self.assertEqual(1, t1.get_n())
        self.assertEqual(1, t1.get_n())

        t1.get_m = types.MethodType(
            persisted('_m')(lambda s: getattr(s, 'get_n')()), t1)
        self.assertEqual(1, t1.get_m())
        self.assertEqual(1, t1.get_m())

        setattr(t1.__class__, 'm_val', property(t1.get_m,))
        self.assertEqual(1, t1.m_val)
        self.assertEqual(1, t1.m_val)

    def test_inst_attach(self):
        fac = self.fac
        obj = fac.instance('temp2')
        self.assertTrue(isinstance(obj.aval, int))
        self.assertEqual(1, obj.aval)
        pw = obj._aval_pw
        self.assertTrue(isinstance(pw, PersistedWork))
        self.assertFalse(pw.cache_global)
        obj.aval = 3
        self.assertEqual(3, obj.aval)
        self.assertEqual(3, pw())

    def test_global_attach(self):
        fac = self.fac
        obj = fac.instance('temp4')
        self.assertTrue(isinstance(obj, Temp4))
        self.assertTrue(isinstance(obj.t3, Temp3))
        self.assertEqual(Temp2, obj.t2.__class__)
        self.assertEqual(1, obj.t2.aval)
        self.assertEqual(3, obj.t3.bval)

        obj = fac.instance('temp4')
        self.assertTrue(isinstance(obj, Temp4))
        self.assertTrue(isinstance(obj.t2, Temp2))
        self.assertEqual(1, obj.t2.aval)
        self.assertEqual(3, obj.t3.bval)

        obj.t2.aval = 4
        obj.t3.bval = 10
        obj = fac.instance('temp4')
        self.assertTrue(isinstance(obj, Temp4))
        self.assertTrue(isinstance(obj.t2, Temp2))
        self.assertEqual(4, obj.t2.aval)
        self.assertEqual(3, obj.t3.bval)

        obj = fac.instance('temp2')
        self.assertTrue(isinstance(obj.aval, int))
        self.assertEqual(1, obj.aval)

        self.assertRaises(RedefinedInjectionError, lambda: fac.instance('temp5'))
        self.assertRaises(RedefinedInjectionError, lambda: fac.instance('temp6'))

        # assert class level tracking in the import factory
        fac = ImportConfigFactory(self.conf)
        self.assertRaises(RedefinedInjectionError, lambda: fac.instance('temp5'))
        self.assertRaises(RedefinedInjectionError, lambda: fac.instance('temp6'))


class TestPersistShare(unittest.TestCase):
    def setUp(self):
        self.conf = Config('test-resources/test-persist-attach.conf')

    def test_not_shared(self):
        fac = ImportConfigFactory(self.conf)
        temp2_a = fac.instance('temp2')
        temp2_b = fac.instance('temp2')
        self.assertEqual(1, temp2_a.aval)
        self.assertEqual(1, temp2_b.aval)
        temp2_a.aval = 2
        self.assertEqual(2, temp2_a.aval)
        self.assertEqual(1, temp2_b.aval)
        self.assertNotEqual(id(temp2_a), id(temp2_b))

        temp7 = fac.instance('temp7')
        self.assertEqual(1, temp7.t2.aval)
        self.assertEqual(3, temp7.t3.bval)

    def test_shared(self):
        fac = ImportConfigFactory(self.conf, shared=True)
        temp2_a = fac.instance('temp2')
        temp2_b = fac.instance('temp2')
        temp3 = fac.instance('temp3')

        self.assertEqual(1, temp2_a.aval)
        self.assertEqual(1, temp2_b.aval)
        temp2_a.aval = 2
        self.assertEqual(2, temp2_a.aval)
        self.assertEqual(2, temp2_b.aval)
        self.assertEqual(id(temp2_a), id(temp2_b))

        temp7 = fac.instance('temp7')
        self.assertEqual(2, temp7.t2.aval)
        self.assertEqual(3, temp7.t3.bval)

        self.assertEqual(3, temp3.bval)
        self.assertEqual(3, temp7.t3.bval)
        temp3.bval = 10
        self.assertEqual(10, temp3.bval)
        self.assertEqual(10, temp7.t3.bval)

        self.assertEqual(id(temp3), id(temp7.t3))

    def test_shared_consistent_state(self):
        self.test_not_shared()
        self.test_shared()
        self.test_not_shared()
        self.test_shared()
