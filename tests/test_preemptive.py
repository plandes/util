from typing import Iterable, Any
import unittest
from zensols.persist import ReadOnlyStash, PreemptiveStash


class RangeStash(ReadOnlyStash):
    def __init__(self, n: int, end: int = None):
        super().__init__()
        self.n = n
        self.end = end
        self.keyed = False
        self.loaded = False

    def load(self, name: str) -> Any:
        self.loaded = True
        if self.exists(name):
            return name

    def keys(self) -> Iterable[str]:
        self.keyed = True
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


class TestPreemptiveStash(unittest.TestCase):
    def setUp(self):
        self.rs = RangeStash(3)
        self.pe = PreemptiveStash(self.rs)

    def test_data_first(self):
        self.assertFalse(self.rs.keyed)
        self.assertFalse(self.rs.loaded)
        self.assertEqual(((0, 0), (1, 1), (2, 2)), tuple(self.pe))
        self.assertTrue(self.pe.has_data)
        self.assertTrue(self.rs.keyed)
        self.assertTrue(self.rs.loaded)

    def test_has_data_first(self):
        self.assertFalse(self.rs.keyed)
        self.assertFalse(self.rs.loaded)
        self.assertTrue(self.pe.has_data)
        self.assertTrue(self.rs.keyed)
        self.assertFalse(self.rs.loaded)
