import unittest
from io import StringIO
from zensols.config import IniConfig, ImportConfigFactory


CONFIG: str = """
[f1]
class_name = test_fac_lifecycle.Foo
"""


class Foo(object):
    pass


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
