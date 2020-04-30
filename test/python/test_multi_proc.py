import logging
import unittest
from zensols.persist import (
    DelegateStash,
    StashMapReducer,
    FunctionStashMapReducer,
    ReadOnlyStash,
)

logger = logging.getLogger(__name__)


class RangeStash(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStash, self).__init__()
        self.n = n

    def load(self, name: str):
        return name

    def keys(self):
        return range(self.n)


class IncMapReducer(StashMapReducer):
    def _map(self, id: str, val):
        return val + 1


class IncSumMapReducer(StashMapReducer):
    def _map(self, id: str, val):
        return val + 1

    def _reduce(self, vals):
        return sum(vals)


def inc2(id, val):
    return val + 2


class TestMultiProc(unittest.TestCase):
    def test_key_group_size(self):
        mp = StashMapReducer(RangeStash(10), 2)
        self.assertEqual(5, mp.key_group_size)
        mp = StashMapReducer(RangeStash(10), 3)
        self.assertEqual(4, mp.key_group_size)
        mp = StashMapReducer(RangeStash(10), 1)
        self.assertEqual(10, mp.key_group_size)
        mp = StashMapReducer(RangeStash(10), 20)
        self.assertEqual(1, mp.key_group_size)
        mp = StashMapReducer(RangeStash(10), 100)
        self.assertEqual(1, mp.key_group_size)

    def test_multi_proc(self):
        mp = IncMapReducer(RangeStash(10), 2)
        self.assertEqual(((1, 2, 3, 4, 5), (6, 7, 8, 9, 10)), tuple(mp()))
        mp = IncSumMapReducer(RangeStash(10), 2)
        self.assertEqual((15, 40), tuple(mp()))

    def test_func(self):
        stash = RangeStash(10)
        dat = FunctionStashMapReducer.map_func(stash, func=inc2, n_workers=2)
        self.assertEqual(((2, 3, 4, 5, 6), (7, 8, 9, 10, 11)), tuple(dat))
