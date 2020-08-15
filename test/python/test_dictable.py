from typing import List
from dataclasses import dataclass, field
import sys
import logging
from io import StringIO
import unittest
from zensols.config import Dictable

logger = logging.getLogger(__name__)
if 0:
    logging.basicConfig(level=logging.WARN)
    logger.setLevel(logging.DEBUG)


@dataclass
class Name(object):
    first: str
    last: str


@dataclass
class Person(Dictable):
    name: str
    age: int
    ssn: str = field(repr=False)


@dataclass
class Employee(Person):
    _DICTABLE_FORMATS = {float: '{:.3f}'}
    salary: float


@dataclass
class Company(Dictable):
    staff: List[Employee]


class TestDictable(unittest.TestCase):
    def setUp(self):
        self.paul = Person(Name('paul', 'smith'), 23, '000-341-1057')
        self.emp_paul = Employee(Name('paul', 'smith'), 23, '000-341-1057', 10.23)
        self.emp_jan = Employee(Name('jan', 'doe'), 21, '999-341-1057', 15.56)
        self.paulco = Company([self.emp_paul, self.emp_jan])
        self.maxDiff = sys.maxsize

    def test_fields(self):
        shd = "Person(name=Name(first='paul', last='smith'), age=23)"
        self.assertEqual(shd, str(self.paul))
        dct = self.paul.asdict()
        shd = {'age': 23,
               'name': {'first': 'paul', 'last': 'smith'}}
        self.assertEqual(shd, dct)

    def test_format(self):
        shd = "Employee(name=Name(first='paul', last='smith'), age=23, salary=10.230)"
        self.assertEqual(shd, str(self.emp_paul))
        dct = self.emp_paul.asdict()
        shd = {'name': {'first': 'paul', 'last': 'smith'},
               'age': 23,
               'salary': '10.230'}
        self.assertEqual(shd, dct)
        shd = "name=Name(first='paul', last='smith'), age=23"
        self.assertEqual(shd, self.paul._get_description())
        shd = "name=Name(first='paul', last='smith'), age=23, salary=10.230"
        self.assertEqual(shd, self.emp_paul._get_description())

    def test_composite(self):
        shd = ("Company(staff=[Employee(name=Name(first='paul', last='smith'), age=23, salary=10.23), " +
               "Employee(name=Name(first='jan', last='doe'), age=21, salary=15.56)])")
        self.assertEqual(shd, str(self.paulco))
        dct = self.paulco.asdict()
        shd = {'staff': [{'age': 23,
                          'name': {'first': 'paul', 'last': 'smith'},
                          'salary': '10.230'},
                         {'age': 21,
                          'name': {'first': 'jan', 'last': 'doe'},
                          'salary': '15.560'}]}
        self.assertEqual(shd, dct)

    def test_write(self):
        sio = StringIO()
        self.paulco.write(writer=sio)
        shd = """\
staff:
    name:
        first: paul
        last: smith
    age: 23
    salary: 10.230
    name:
        first: jan
        last: doe
    age: 21
    salary: 15.560\n"""
        self.assertEqual(shd, sio.getvalue())

    def test_json(self):
        shd = """\
{
    "staff": [
        {
            "name": {
                "first": "paul",
                "last": "smith"
            },
            "age": 23,
            "salary": "10.230"
        },
        {
            "name": {
                "first": "jan",
                "last": "doe"
            },
            "age": 21,
            "salary": "15.560"
        }
    ]
}"""
        json = self.paulco.asjson(indent=4)
        self.assertEqual(shd, json)
