from typing import Tuple
from dataclasses import dataclass, field
from zensols.config import Dictable


@dataclass
class Person(Dictable):
    name: str
    age: int
    salary: float


@dataclass
class Department(Dictable):
    name: str
    employees: Tuple[Person] = field(default_factory=lambda: ())

    def __str__(self):
        emp_names = ', '.join(map(lambda p: p.name, self.employees))
        return f"{self.name}: {emp_names}"
