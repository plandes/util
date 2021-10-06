from typing import Any, Iterable
import unittest
from zensols.persist import (
    DelegateDefaults,
    FactoryStash,
    DictionaryStash,
    CacheStash,
    ReadOnlyStash,
    UnionStash,
    ProtectiveStash,
)


class IncStash(ReadOnlyStash):
    def __init__(self):
        super().__init__()
        self.c = 0

    def load(self, name: str):
        self.c += 1
        return f'{name}-{self.c}'

    def keys(self) -> Iterable[str]:
        return ()


class RangeStash(ReadOnlyStash):
    def __init__(self, n, end: int = None):
        super().__init__()
        self.n = n
        self.end = end

    def load(self, name: str) -> Any:
        if self.exists(name):
            return name

    def keys(self) -> Iterable[str]:
        if self.end is not None:
            return range(self.n, self.end)
        else:
            return range(self.n)

    def exists(self, name: str) -> bool:
        n = int(name)
        if self.end is None:
            if (n >= self.n):
                return False
        elif (n < self.n) or (n >= self.end):
            return False
        return True


class ExStash(DictionaryStash):
    def __init__(self, error_val: str):
        super().__init__()
        self.error_val = error_val

    def dump(self, name: str, inst: Any):
        if inst == self.error_val:
            raise ValueError(f'Test exception for name {name}')
        else:
            super().dump(name, inst)


class TestStash(unittest.TestCase):
    def setUp(self):
        DelegateDefaults.CLASS_CHECK = True

    def _test_dump(self, ds):
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

    def test_dict(self):
        ds = DictionaryStash()
        self._test_dump(ds)

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
        self.assertEqual(0, stash[0])

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
        # still has all the members since a caching stash is a read only stash
        self.assertEqual(5, len(stash))

    def _test_delegate(self, stash1, stash2):
        #stash1 = RangeStash(3)
        #stash2 = RangeStash(3, 5)
        stash3 = UnionStash((stash1, stash2))
        self.assertEqual(3, len(stash1))
        self.assertEqual(2, len(stash2))
        self.assertEqual(5, len(stash3))
        self.assertEqual(((0, 0), (1, 1), (2, 2)), tuple(stash1))
        self.assertEqual(((3, 3), (4, 4)), tuple(stash2))
        self.assertEqual(((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)), tuple(stash3))
        self.assertEqual(([0, 1, 2], [3, 4]), tuple(stash3.key_groups(3)))
        self.assertEqual(([0, 1], [2, 3], [4,]), tuple(stash3.key_groups(2)))
        self.assertEqual(([0, 1, 2, 3], [4,]), tuple(stash3.key_groups(4)))
        self.assertEqual(([0, 1, 2, 3, 4,],), tuple(stash3.key_groups(5)))
        self.assertEqual(([0, 1, 2, 3, 4,],), tuple(stash3.key_groups(6)))
        self.assertTrue(stash1.exists(0))
        self.assertTrue(stash1.exists(1))
        self.assertTrue(stash1.exists(2))
        self.assertFalse(stash1.exists(3))
        self.assertFalse(stash2.exists(2))
        self.assertTrue(stash2.exists(3))
        self.assertTrue(stash2.exists(4))
        self.assertFalse(stash2.exists(5))

    def test_delegate_to_delegate(self):
        stash1 = RangeStash(3)
        stash2 = RangeStash(3, 5)
        self._test_delegate(stash1, stash2)

    def test_protective_happy(self):
        stash1 = RangeStash(3)
        stash2 = RangeStash(3, 5)
        pstash = ProtectiveStash(stash2, True)
        self._test_delegate(stash1, pstash)
        ds = ExStash(None)
        ps = ProtectiveStash(ds, True)
        self._test_dump(ps)

    def test_protective_exception(self):
        err_val = '<error value>'
        ds = ExStash(err_val)
        ps = ProtectiveStash(ds, False)
        self._test_dump(ps)
        ps.dump('b', err_val)
        ex = ps['b']
        self.assertEqual(ValueError, type(ex))
        self.assertEqual('Test exception for name b', str(ex))
