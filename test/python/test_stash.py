import logging
import unittest
from zensols.persist import (
    FactoryStash,
    DictionaryStash,
    CacheStash,
    ReadOnlyStash,
)

logger = logging.getLogger(__name__)


class IncStash(ReadOnlyStash):
    def __init__(self):
        super().__init__()
        self.c = 0

    def load(self, name: str):
        self.c += 1
        return f'{name}-{self.c}'

    def keys(self):
        return ()


class RangeStash(ReadOnlyStash):
    def __init__(self, n):
        super().__init__()
        self.n = n

    def load(self, name: str):
        n = int(name)
        if n >= self.n:
            return None
        return name

    def keys(self):
        return range(self.n)


class TestStash(unittest.TestCase):
    def test_dict(self):
        ds = DictionaryStash()
        self.assertEqual(0, len(ds.keys()))
        self.assertFalse(ds.exists('a'))
        ds.dump('a', 1)
        self.assertTrue(ds.exists('a'))
        self.assertEqual(1, ds.load('a'))
        self.assertEqual(1, ds['a'])
        self.assertEqual(1, ds.get('a'))
        self.assertEqual(2, ds.get('b', 2))
        ds.delete('a')
        self.assertEqual(0, len(ds.keys()))
        self.assertFalse(ds.exists('a'))

    def test_caching(self):
        ins = IncStash()
        ds = DictionaryStash()
        st = FactoryStash(ds, ins)
        self.assertEqual('first-1', st['first'])
        self.assertEqual('first-1', st.get('first'))
        self.assertEqual('second-2', st['second'])
        self.assertEqual('first-1', st['first'])
        self.assertEqual('second-2', st['second'])
        self.assertEqual(2, len(st))
        self.assertEqual(set('first second'.split()), st.keys())

    def test_key_group(self):
        stash = RangeStash(5)
        self.assertEqual(((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)), tuple(stash))
        self.assertEqual(([0, 1, 2], [3, 4]), tuple(stash.key_groups(3)))
        self.assertEqual(([0, 1], [2, 3], [4,]), tuple(stash.key_groups(2)))
        self.assertEqual(([0, 1, 2, 3], [4,]), tuple(stash.key_groups(4)))
        self.assertEqual(([0, 1, 2, 3, 4,],), tuple(stash.key_groups(5)))
        self.assertEqual(([0, 1, 2, 3, 4,],), tuple(stash.key_groups(6)))

    def test_not_exist(self):
        stash = RangeStash(5)
        self.assertTrue(stash.exists(4))
        self.assertFalse(stash.exists(5))
        self.assertEqual(4, stash.get(4))
        self.assertEqual(None, stash.get(5))
        self.assertEqual(None, stash.get(6))
        self.assertFalse(stash.exists(6))
        self.assertEqual('nada', stash.get(6, 'nada'))

    def test_cache_stash(self):
        print()
        stash = CacheStash(delegate=RangeStash(5))
        self.assertEqual(((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)), tuple(stash))
        self.assertEqual({0: 0, 1: 1, 2: 2, 3: 3, 4: 4}, stash.cache_stash.data)
        stash.delete(3)
        self.assertEqual({0: 0, 1: 1, 2: 2, 4: 4}, stash.cache_stash.data)
        # range stash doesn't implement delete
        self.assertEqual(((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)), tuple(stash))
        self.assertEqual(((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)),
                         tuple(sorted(stash.cache_stash, key=lambda x: x[0])))
        stash.clear()
        # disabled since a caching stash is read only
        #self.assertEqual(0, len(stash))
        #self.assertEqual((), tuple(stash.keys()))
