from typing import Tuple
from dataclasses import dataclass, field
import unittest
from zensols.config import (
    Dictable, Settings, YamlConfig, ImportConfigFactory, FactoryError
)


@dataclass
class DriversLicense(Dictable):
    state: str
    number: str


@dataclass
class Person(Dictable):
    name: str
    age: int
    salary: float = field(default=15.)
    drivers_license: DriversLicense = field(default=None)


@dataclass
class Department(Dictable):
    name: str
    employees: Tuple[Person]


class TestYamlDataclass(unittest.TestCase):
    def setUp(self):
        self.conf = YamlConfig('test-resources/dataclass-test.yml')
        self.fac = ImportConfigFactory(self.conf)

    def test_ref(self):
        instances: Settings = self.fac('croot.instances')
        self.assertEqual(Settings, type(instances))
        dept: Department = instances.dept
        self.assertEqual(Department, type(dept))
        self.assertEqual('hr', dept.name)
        self.assertEqual(tuple, type(dept.employees))
        self.assertEqual(2, len(dept.employees))
        should = (Person(name='bob', age=21, salary=15.5,
                         drivers_license=None),
                  Person(name='jill', age=25, salary=12.5,
                         drivers_license=DriversLicense(
                             state='IL', number='598430IL')))
        self.assertEqual(should, dept.employees)

    def test_inline(self):
        instances: Settings = self.fac('croot.inlines')
        self.assertEqual(Settings, type(instances))
        dept: Department = instances.dept2
        self.assertEqual(Department, type(dept))
        self.assertEqual('it', dept.name)
        self.assertEqual(tuple, type(dept.employees))
        should = (Person(name='martha', age=65, salary=10.1,
                         drivers_license=None),
                  Person(name='bill', age=32, salary=58.2,
                         drivers_license=DriversLicense(
                             state='CA', number='6901')))
        self.assertEqual(should, dept.employees)

    def test_bad_config(self):
        with self.assertRaisesRegex(FactoryError, '^Not a valid class name:'):
            self.fac('croot.instances-bad')
