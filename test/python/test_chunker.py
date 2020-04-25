import logging
import unittest
from zensols.persist import chunks

logger = logging.getLogger(__name__)


class TestChunker(unittest.TestCase):
    def test_persister(self):
        self.assertEqual(([0, 1, 2], [3, 4, 5], [6, 7, 8]),
                         tuple(chunks(range(9), 3)))
        self.assertEqual(([0, 1, 2], [3, 4, 5], [6, 7, 8], [9]),
                         tuple(chunks(range(10), 3)))
        self.assertEqual((), tuple(chunks(range(0), 3)))
        self.assertEqual(([0],), tuple(chunks(range(1), 3)))
        self.assertEqual(([1, 2, 3], [4, 5, 6], [7, 8, 9], [10]),
                         tuple(chunks(map(lambda x: x + 1, range(10)), 3)))
