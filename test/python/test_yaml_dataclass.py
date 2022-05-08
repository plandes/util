from typing import Tuple
from dataclasses import dataclass, field
import unittest
from zensols.config import Dictable, Settings, YamlConfig, ImportConfigFactory


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
    def test_dc(self):
        conf = YamlConfig('test-resources/dataclass-test.yml')
        fac = ImportConfigFactory(conf)
        instances: Settings = fac('croot.instances')
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
