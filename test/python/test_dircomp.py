from dataclasses import dataclass, asdict
from typing import Any
import logging
import shutil
from pathlib import Path
import unittest
from zensols.persist import DelegateDefaults, DirectoryCompositeStash

logger = logging.getLogger(__name__)


class DcsTestStash(DirectoryCompositeStash):
    def _to_composite(self, inst: Any) -> Any:
        return self._to_dict(inst, 'agg')


@dataclass
class DataItem(object):
    apple: int
    orange: int
    dog: str
    cat: str

    def __post_init__(self):
        self.agg = asdict(self)


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
        cstashes = stash.composite_stashes
        self.assertEqual(set(cstashes.keys()), set('apple orange dog cat'.split()))
        gnames = set(map(lambda s: s.group_name, cstashes.values()))
        self.assertEqual(gnames, set('cat-dog apple-orange '.split()))
        self.assertEqual(set(stash.stash_by_group.keys()), set('cat-dog apple-orange '.split()))

    def test_to_dict(self):
        path = self.targdir / 'to_dict'
        stash = DcsTestStash(path, self.groups)
        self.assertFalse(path.exists())
        di = DataItem(1, 2, 'rover', 'fuzzy')
        composite = stash._to_composite(di)[2]
        self.assertEqual(set(composite.keys()), set('apple-orange cat-dog'.split()))
        s1 = composite['apple-orange']
        s2 = composite['cat-dog']
        self.assertEqual({'apple': 1, 'orange': 2}, s1)
        self.assertEqual({'dog': 'rover', 'cat': 'fuzzy'}, s2)

    def test_persist(self):
        path = self.targdir / 'persist'
        inst_path = path / DcsTestStash.INSTANCE_DIRECTORY_NAME
        stash = DcsTestStash(path, self.groups)
        di = DataItem(1, 2, 'rover', 'fuzzy')
        stash.dump('1', di)
        self.assertTrue(path.is_dir())
        self.assertTrue(inst_path.is_dir())
        self.assertTrue((inst_path / '1.dat').is_file())
        self.assertTrue((path / 'apple-orange').is_dir())
        self.assertTrue((path / 'apple-orange/1.dat').is_file())
        self.assertTrue((path / 'cat-dog').is_dir())
        self.assertTrue((path / 'cat-dog/1.dat').is_file())
