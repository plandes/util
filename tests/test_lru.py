from logutil import LogTestCase
from collections import OrderedDict
from zensols.persist import LRUCacheStash


class TestLRUStash(LogTestCase):
    def _test_stash(self, stash: LRUCacheStash):
        self.assertEqual(OrderedDict, type(stash.data))
        self.assertEqual(0, len(stash.data))

        stash.dump('a', 1)
        self.assertEqual(1, len(stash.data))
        self.assertEqual(('a',), tuple(stash.keys()))
        self.assertEqual((1,), tuple(stash.values()))
        self.assertEqual(1, stash['a'])
        self.assertEqual(1, stash.load('a'))
        with self.assertRaisesRegex(KeyError, r"^'b'"):
            stash['b']

        stash.dump('b', 2)
        self.assertEqual(2, len(stash.data))
        self.assertEqual(['a', 'b'], sorted(stash.keys()))
        self.assertEqual([1, 2], sorted(stash.values()))
        self.assertEqual(2, stash['b'])
        self.assertEqual(1, stash.load('a'))
        self.assertEqual(2, stash.load('b'))

        stash.dump('c', 3)
        self.assertEqual(2, len(stash.data))
        self.assertEqual(['b', 'c'], sorted(stash.keys()))
        self.assertEqual([2, 3], sorted(stash.values()))
        self.assertEqual(3, stash['c'])
        self.assertEqual(None, stash.get('a'))
        with self.assertRaisesRegex(KeyError, r"^'a'"):
            stash['a']

    def test_stash(self):
        stash = LRUCacheStash(2)
        self._test_stash(stash)

        stash.clear()
        self._test_stash(stash)
