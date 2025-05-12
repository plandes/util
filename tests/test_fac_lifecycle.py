from dataclasses import dataclass, field
import unittest
from io import StringIO
from zensols.config import IniConfig, ImportConfigFactory


CONFIG: str = """
[f1]
class_name = test_fac_lifecycle.Foo

[f2]
class_name = test_fac_lifecycle.FooHolder
held = instance: f1

[f3]
class_name = test_fac_lifecycle.FooHolder
held = instance: f1

[f4]
class_name = test_fac_lifecycle.FooHolder
held = instance({'share': 'evict'}): f1

[f5]
class_name = test_fac_lifecycle.FooHolder
held = instance({'share': 'evict'}): f1

[f6]
class_name = test_fac_lifecycle.FooHolder
held = instance({'share': 'deep'}): f1
"""


class Foo(object):
    pass


@dataclass
class FooHolder(object):
    held: Foo = field()


class TestFactoryLifecycle(unittest.TestCase):
    def setUp(self):
        self.fac = ImportConfigFactory(IniConfig(StringIO(CONFIG)))

    def test_clear(self):
        f1 = self.fac.instance('f1')
        self.assertEqual(Foo, type(f1))
        self.assertTrue('f1' in self.fac._shared)
        self.assertEqual(id(self.fac.clear_instance('f1')), id(f1))

    def test_new(self):
        f1 = self.fac.new_instance('f1')
        self.assertEqual(Foo, type(f1))
        self.assertFalse('f1' in self.fac._shared)

        f2 = self.fac.new_instance('f1')
        self.assertNotEqual(id(f1), id(f2))

        self.assertTrue(self.fac.clear_instance('f1') is None)

    def test_share(self):
        h2 = self.fac.instance('f2')
        h3 = self.fac.instance('f3')
        # the held foo is cleared from the shared cache
        self.fac.instance('f4')
        h5 = self.fac.instance('f5')
        self.assertEqual(id(h2.held), id(h3.held))
        self.assertEqual(id(h2.held), id(h3.held))
        self.assertNotEqual(id(h2.held), id(h5.held))

    def test_deep_share(self):
        h2 = self.fac.instance('f2')
        # entire data structure is copied
        h6 = self.fac.instance('f6')
        self.assertNotEqual(id(h2.held), id(h6.held))
