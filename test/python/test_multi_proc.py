from typing import List, Tuple, Iterable, Any
from dataclasses import dataclass
import unittest
import shutil
import os
from itertools import chain
from pathlib import Path
from zensols.config import IniConfig, ImportConfigFactory
from zensols.persist import ReadOnlyStash
from zensols.multi import MultiProcessStash


class RangeStash(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStash, self).__init__()
        self.n = n

    def load(self, name: str):
        return name

    def keys(self):
        return range(self.n)


@dataclass
class RangeMultiProcessStash(MultiProcessStash):
    n: int

    def _create_data(self) -> Iterable[Any]:
        return range(self.n)

    def _process(self, chunk: List[Any]) -> Iterable[Tuple[str, Any]]:
        iset: List[int] = chunk
        yield (str(min(iset)), {'pid': os.getpid(), 'iset': iset})


class TestMultiProcessStash(unittest.TestCase):
    def setUp(self):
        self.conf = IniConfig('test-resources/test-multi.conf')
        self.fac = ImportConfigFactory(self.conf)
        self.target_path = Path('target')
        if self.target_path.exists():
            shutil.rmtree(self.target_path)

    def test_range(self):
        stash = self.fac('range_multi')
        n_elems = 9
        self.assertEqual(RangeMultiProcessStash, type(stash))
        self.assertEqual(n_elems, stash.n)
        self.assertEqual(3, len(stash))
        self.assertEqual({'0', '3', '6'}, set(stash.keys()))
        pids = set(map(lambda x: x['pid'], stash.values()))
        # this keeps failing in GitHub workflow CL testing
        if os.environ.get('NO_TEST_MULTI_PROC_PIDS') != '1':
            self.assertTrue(len(pids) > 1)
        vals = chain.from_iterable(map(lambda x: x['iset'], stash.values()))
        self.assertEqual(list(range(n_elems)), sorted(vals))
