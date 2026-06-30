from dataclasses import dataclass, field
from zensols.config import Dictable
from zensols.dataclasses.inspect import DataclassMetadata
from logutil import LogTestCase


@dataclass
class Person(Dictable):
    """Represents a human.

    """
    name: str = field()
    """The person's name."""

    age: int = field()
    """The age of the person in years."""


class TestDataclassInspect(LogTestCase):
    DEBUG: bool = False

    def _test_inspect(self):
        dm = DataclassMetadata(Person)
        self.assertEqual(2, len(dm.fields))
        self.assertEqual(2, len(dm.fields_by_order))
        self.assertEqual(str, dm.fields['name'].dtype)
        self.assertEqual(int, dm.fields['age'].dtype)
        self.assertEqual("The person's name.", dm.fields['name'].doc.text)
        self.assertEqual('Represents a human.', dm.doc.text)

    def test_flatten(self):
        should = {'class_type': 'test_dataclass_inspect.Person',
                  'doc': {'params': {}, 'text': 'Represents a human.'},
                  'fields_by_order':
                  [{'doc': {'params': {}, 'text': "The person's name."},
                    'dtype': 'str',
                    'kwargs': {},
                    'name': 'name'},
                   {'doc': {'params': {},
                            'text': 'The age of the person in years.'},
                    'dtype': 'int',
                    'kwargs': {},
                    'name': 'age'}]}
        dm = DataclassMetadata(Person)
        if self.DEBUG:
            from pprint import pprint
            print()
            pprint(dm.asflatdict())
        self.assertEqual(should, dm.asflatdict())
