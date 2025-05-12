from typing import Tuple, Dict
from dataclasses import dataclass
import unittest
from itertools import chain
from pathlib import Path
import shutil
from zensols.config import (
    FactoryError, IniConfig, ImportConfigFactory, Settings
)
from zensols.persist import (
    DelegateDefaults, DirectoryStash, ReadOnlyStash, FactoryStash
)


if 0:
    import logging
    logging.basicConfig(level=logging.DEBUG)


class RangeStashThisMod(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStashThisMod, self).__init__()
        self.n = n
        self.prefix = ''

    def load(self, name: str):
        return f'{self.prefix}{name}'

    def keys(self):
        return map(str, range(self.n))


@dataclass
class RangeHolder(object):
    some_range: object


@dataclass
class StashHolder(object):
    stash: DirectoryStash


@dataclass
class StashCollection(object):
    stashes: Tuple[ReadOnlyStash]

    def values(self):
        return chain.from_iterable(map(lambda s: s.values(), self.stashes))


@dataclass
class StashMap(object):
    stashes: Dict[str, ReadOnlyStash]

    def values(self):
        return chain.from_iterable(map(lambda s: s.values(), self.stashes))


class TestStashFactory(unittest.TestCase):
    def setUp(self):
        self.conf = IniConfig('test-resources/stash-factory.conf')
        self.target_path = Path('target')
        if self.target_path.exists():
            shutil.rmtree(self.target_path)
        DelegateDefaults.CLASS_CHECK = True

    def test_create_same_module(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range3_stash')
        self.assertTrue(isinstance(inst, RangeStashThisMod))
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(6))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(6))), set(inst))

    def test_create_external(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range1_stash')
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(5))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(5))), set(inst))

    def test_create_external2(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range5_stash')
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(7))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(7))), set(inst))

    def test_delegate_create(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range2_stash')
        self.assertFalse(self.target_path.exists())
        self.assertTrue(isinstance(inst, FactoryStash))
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(5))), set(inst))
        self.assertTrue(self.target_path.is_dir())
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'{x}'), range(5))), set(inst))

    def test_instance_param(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range_holder')
        self.assertTrue(isinstance(inst, RangeHolder))
        arange = inst.some_range
        self.assertTrue(isinstance(arange, RangeStashThisMod))
        self.assertEqual(123, arange.n)

    def test_not_import(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('stash_holder')
        self.assertTrue(isinstance(inst, StashHolder))
        stash = inst.stash
        self.assertTrue(isinstance(stash, DirectoryStash))
        path = stash.path
        self.assertTrue(isinstance(path, Path))

    def test_with_badkey(self):
        fac = ImportConfigFactory(self.conf)
        self.assertRaises(
            FactoryError, lambda: fac.instance('stash_holder_badkey'))

    def test_with_import(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('stash_holder_param')
        self.assertTrue(isinstance(inst, StashHolder))
        stash = inst.stash
        self.assertTrue(isinstance(stash, DirectoryStash))
        path = stash.path
        self.assertTrue(isinstance(path, Path))
        self.assertTrue('range10_stash', path.name)

    def test_no_class_name(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('no_class_name')
        self.assertTrue(isinstance(inst, Settings))
        self.assertEqual(1.23, inst.afloat)
        self.assertEqual(123, inst.anint)
        self.assertEqual('some string', inst.astr)
        self.assertEqual([1, 2, 3], inst.anarray)
        sh = ("""{"afloat": 1.23, "anint": 123, "astr": "some string", """ +
              """"anarray": [1, 2, 3]}""")
        self.assertEqual(sh, inst.asjson())

    def test_instance_list(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('stash_collection')
        self.assertEqual(StashCollection, type(inst))
        stashes = inst.stashes
        self.assertEqual(tuple, type(stashes))
        self.assertEqual(2, len(stashes))
        self.assertEqual('RangeStash1', stashes[0].__class__.__name__)
        self.assertEqual(RangeStashThisMod, stashes[1].__class__)
        self.assertEqual(('0', '1', '2', '3', '4', '0', '1', '2', '3', '4', '5'),
                         tuple(inst.values()))

    def test_instance_dict(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('stash_map')
        self.assertEqual(StashMap, type(inst))
        stashes = inst.stashes
        self.assertEqual(dict, type(stashes))
        self.assertEqual(2, len(stashes))
        self.assertEqual(set('r1 r3'.split()), set(stashes.keys()))
        self.assertEqual('RangeStash1', stashes['r1'].__class__.__name__)
        self.assertEqual(RangeStashThisMod, stashes['r3'].__class__)

    def test_instance_bad_type(self):
        fac = ImportConfigFactory(self.conf)
        self.assertRaises(FactoryError,
                          lambda: fac.instance('stash_error_type'))
