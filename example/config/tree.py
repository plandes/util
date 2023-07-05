#!/usr/bin/env python

"""Demonstrates the ``tree`` application configuration directive.

"""

from typing import Dict, Any
from io import StringIO
from dataclasses import dataclass
from zensols.config import YamlConfig, ImportConfigFactory


CONFIG = """
instance:
  employee: >-
    tree({'param': {'name': 'data.person',
                    'age': 25}}): data
data:
  person:
    class_name: tree.Person
    name: Paul
    age: 23
    deep_record:
      more:
        nodes: here
"""


@dataclass
class Person(object):
    name: str
    age: int
    deep_record: Dict[str, Any]


def main():
    config = YamlConfig(StringIO(CONFIG))
    fac = ImportConfigFactory(config)
    person = fac('instance')
    print(person)


if (__name__ == '__main__'):
    main()
