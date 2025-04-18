from dataclasses import dataclass, asdict, field, InitVar
import random
import collections
import shutil
from pathlib import Path
import unittest
from zensols.persist import (
    DelegateDefaults,
    DirectoryCompositeStash,
    MissingDataKeysError,
    PersistableError,
)


class DcsTestStash(DirectoryCompositeStash):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, attribute_name='agg', **kwargs)


@dataclass
class DataItem(object):
    apple: int
    orange: int
    dog: str
    cat: str
    is_ordered: InitVar[bool] = field(default=False)

    def __post_init__(self, is_ordered: bool):
        data = asdict(self)
        agg = collections.OrderedDict() if is_ordered else {}
        keys = list(data.keys())
        random.shuffle(keys)
        for k in keys:
            agg[k] = data[k]
        self.agg = agg

    def __str__(self):
        return f'{super().__str__()}, agg={self.agg}'


class TestDirectoryCompStash(unittest.TestCase):
    def setUp(self):
        DelegateDefaults.CLASS_CHECK = True
        targdir = Path('target/ctmp')
        if targdir.exists():
            shutil.rmtree(targdir)
        self.targdir = targdir
        self.groups = (set('apple orange'.split()), set('dog cat'.split()))

    def test_create(self):
        path = self.targdir / 'create'
        stash = DcsTestStash(path, groups=self.groups)
        stash_path = self.targdir / 'create' / DcsTestStash.INSTANCE_DIRECTORY_NAME
        self.assertEqual(stash_path, stash.path)
        cstashes = stash._stash_by_attribute
        self.assertEqual(set(cstashes.keys()), set('apple orange dog cat'.split()))
        gnames = set(map(lambda s: s.group_name, cstashes.values()))
        self.assertEqual(gnames, set('cat-dog apple-orange '.split()))
        self.assertEqual(set(stash._stash_by_group.keys()), set('cat-dog apple-orange '.split()))

    def test_dict_to_composite(self):
        path = self.targdir / 'to_dict'
        stash = DcsTestStash(path, self.groups)
        self.assertFalse(path.exists())
        di = DataItem(1, 2, 'rover', 'fuzzy')
        composite = stash._to_composite(di.agg)[1]
        composite = dict(composite)
        self.assertEqual(set(composite.keys()), set('apple-orange cat-dog'.split()))
        s1 = composite['apple-orange']
        s2 = composite['cat-dog']
        self.assertEqual({'apple': 1, 'orange': 2}, s1)
        self.assertEqual({'dog': 'rover', 'cat': 'fuzzy'}, s2)

    def test_dump(self):
        path = self.targdir / 'dump'
        inst_path = path / DcsTestStash.INSTANCE_DIRECTORY_NAME
        stash = DcsTestStash(path, self.groups)
        di = DataItem(1, 2, 'rover', 'fuzzy')
        stash.dump('1', di)
        self.assertTrue(path.is_dir())
        self.assertTrue(inst_path.is_dir())
        self.assertTrue((inst_path / '1.dat').is_file())
        comp_path = path / DcsTestStash.COMPOSITE_DIRECTORY_NAME
        self.assertTrue((comp_path / 'apple-orange').is_dir())
        self.assertTrue((comp_path / 'apple-orange/1.dat').is_file())
        self.assertTrue((comp_path / 'cat-dog').is_dir())
        self.assertTrue((comp_path / 'cat-dog/1.dat').is_file())

    def test_load(self):
        path = self.targdir / 'load'
        stash = DcsTestStash(path, self.groups)
        di = DataItem(1, 2, 'rover', 'fuzzy')
        stash.dump('1', di)
        di2 = stash.load('1')
        self.assertEqual(di.agg, di2.agg)
        self.assertNotEqual(id(di), id(di2))

    def test_load_ordered(self):
        path = self.targdir / 'load-ordered'
        stash = DcsTestStash(path, self.groups)
        tdata = [[2, 3, 'blue', 'paws'],
                 [3, 4, 'stumpy', 'patches'],
                 [5, 10, 'rascal', 'cuddles']]
        for i, idata in enumerate(tdata):
            for ordered in (True, False):
                key = str(i)
                di = DataItem(1, 2, 'rover', 'fuzzy', ordered)
                stash.dump(key, di)
                di2 = stash.load(key)
                self.assertNotEqual(id(di), id(di2))
                self.assertEqual(di.agg, di2.agg)

    def test_load_comp_missing(self):
        path = self.targdir / 'load-comp'
        stash = DcsTestStash(path, self.groups)
        di = DataItem(1, 2, 'rover', 'fuzzy')
        stash.dump('1', di)
        comp_path = path / DcsTestStash.COMPOSITE_DIRECTORY_NAME
        dat_path = comp_path / 'apple-orange' / '1.dat'
        self.assertTrue(dat_path.is_file())
        dat_path = comp_path / 'cat-dog' / '1.dat'
        self.assertTrue(dat_path.is_file())
        dat_path.unlink()
        self.assertRaises(PersistableError, lambda: stash.load('1'))

    def test_load_comp_skip_load(self):
        path = self.targdir / 'load-comp'
        stash = DcsTestStash(path, self.groups, load_keys=set('apple'.split()))
        di = DataItem(1, 2, 'rover', 'fuzzy')
        stash.dump('1', di)
        comp_path = path / DcsTestStash.COMPOSITE_DIRECTORY_NAME
        dat_path = comp_path / 'apple-orange' / '1.dat'
        self.assertTrue(dat_path.is_file())
        dat_path = comp_path / 'cat-dog' / '1.dat'
        self.assertTrue(dat_path.is_file())
        dat_path.unlink()
        di2 = stash.load('1')
        self.assertEqual({'apple': 1}, di2.agg)

    def test_dump_missing(self):
        path = self.targdir / 'dump_missing'
        stash = DcsTestStash(path, self.groups)
        di = DataItem(1, 2, 'rover', 'fuzzy')
        del di.agg['dog']
        try:
            stash.dump('1', di)
            self.assertTrue(False, 'should have thrown exception')
        except MissingDataKeysError as e:
            self.assertEqual({'dog'}, e.keys)
