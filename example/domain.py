from typing import List
from dataclasses import dataclass


@dataclass
class Person(object):
    age: int
    aliases: List[str]


@dataclass
class Organization(object):
    boss: Person
