from dataclasses import dataclass
import unittest
from zensols.config import IniConfig, ImportConfigFactory


@dataclass
class Banana(object):
    color: str


@dataclass
class Basket(object):
    fruit: Banana


class TestFactoryObjectCreate(unittest.TestCase):
    def setUp(self):
        config = IniConfig('test-resources/object-factory.conf')
        self.fac = ImportConfigFactory(config, shared=False)

    def _test_banana(self, inst_name: str, should_color: str):
        basket = self.fac(inst_name)
        self.assertEqual(Basket, basket.__class__)
        banana = basket.fruit
        self.assertEqual(Banana, banana.__class__)
        self.assertEqual(should_color, banana.color)

    def test_object_create(self):
        self._test_banana('basket_instance', 'yellow')
        self._test_banana('basket_instance_2', 'brown')
        self._test_banana('basket_instance_3', 'green')


class TestAlias(unittest.TestCase):
    def setUp(self):
        config = IniConfig('test-resources/object-factory.conf')
        self.fac = ImportConfigFactory(config)

    def test_defer(self):
        basket = self.fac('basket_with_alias')
        self.assertEqual(Basket, basket.__class__)
        banana = basket.fruit
        self.assertEqual(Banana, banana.__class__)
        self.assertEqual('brown', banana.color)
