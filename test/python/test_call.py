from dataclasses import dataclass, field
from io import StringIO
from zensols.config import IniConfig, ImportConfigFactory
from logutil import LogTestCase


CONFIG = """\
[factory]
class_name = test_call.Factory

[car]
class_name = test_call.Car
engine = call({'param': {'method': 'create', 'part_name': 'engine'}}): factory
transmission = call({}): factory
make = call({'param': {'attribute': 'company_name'}}): factory
"""


class Engine(object):
    pass


class Transmission(object):
    pass


@dataclass
class Factory(object):
    company_name: str = field(default='fix or repair daily')

    def create(self, part_name: str) -> Engine:
        if part_name == 'engine':
            return Engine()
        elif part_name == 'transmission':
            return Transmission()
        else:
            raise ValueError(f'Unknown part: {part_name}')

    def __call__(self):
        return self.create('transmission')


@dataclass
class Car(object):
    engine: Engine = field()
    transmission: Transmission = field()
    make: str = field()


class TestArgumentParse(LogTestCase):
    def test_call(self):
        print()
        fac = ImportConfigFactory(IniConfig(StringIO(CONFIG)))
        car = fac('car')
        self.assertEqual(Car, type(car))
        self.assertEqual(Engine, type(car.engine))
        self.assertEqual(Transmission, type(car.transmission))
        self.assertEqual('fix or repair daily', car.make)
