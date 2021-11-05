from typing import List, Tuple
from dataclasses import dataclass, field
from zensols.config import Dictable


@dataclass
class Person(Dictable):
    age: int
    aliases: List[str]


@dataclass
class Organization(Dictable):
    boss: Person
    employees: Tuple[Person] = field(default_factory=lambda: ())
