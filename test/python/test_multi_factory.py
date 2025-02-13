from typing import List, Set
import os
import shutil
import unittest
from pathlib import Path
from zensols.util import Failure
from zensols.config import IniConfig, ImportConfigFactory
from zensols.persist import ReadOnlyStash, DirectoryStash, Stash
from zensols.multi import MultiProcessFactoryStash, MultiProcessRobustStash


class RangeStash(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStash, self).__init__()
        self.n = n

    def load(self, name: str):
        return {'name': name, 'pid': os.getpid()}

    def keys(self):
        return map(str, range(self.n))


class RangeStashFail(RangeStash):
    def __init__(self, n, fails):
        super().__init__(n)
        self.fails = fails

    def load(self, name: str):
        if name in self.fails:
            raise ValueError(f"Key '{name}' is in fail list")
        return super().load(name)


class TestMultiProcessRobustStash(unittest.TestCase):
    def setUp(self):
        self._create_factory()
        self.target_path = Path('target')
        if self.target_path.exists():
            shutil.rmtree(self.target_path)

    def _create_factory(self):
        conf = IniConfig('test-resources/test-multi-factory.conf')
        self.fac = ImportConfigFactory(conf)

    def _test_multi_proc(self, stash: MultiProcessFactoryStash):
        self.assertEqual(RangeStash, type(stash.factory))
        self.assertEqual(DirectoryStash, type(stash.delegate))
        n_elems: int = stash.factory.n
        chunks: int = stash.chunk_size
        n_should_cpus: int = int(n_elems / chunks)
        self.assertEqual(0, stash.workers)
        self.assertFalse(self.target_path.exists())
        self.assertEqual(n_elems, len(stash))
        self.assertTrue(self.target_path.is_dir())
        if os.environ.get('NO_TEST_MULTI_PROC_PIDS') != '1':
            n_cpus = len(set(map(lambda d: d['pid'], stash.values())))
            self.assertTrue(n_cpus > 1)
            self.assertEqual(n_should_cpus, n_cpus)

    def test_multi_proc(self):
        stash = self.fac('range_multi')
        self.assertEqual(MultiProcessFactoryStash, type(stash))
        self._test_multi_proc(stash)

    def test_multi_robust(self):
        stash: Stash = self.fac('robust')
        self.assertEqual(MultiProcessRobustStash, type(stash))

    def test_multi_create_missing_invalidate(self):
        keys: List[str] = ' 3 5 6'.split()
        stash: Stash = self.fac('robust')
        init_len: int = stash.factory.n
        n_missing: int = init_len - len(keys)
        self.assertEqual(MultiProcessRobustStash, type(stash))
        self.assertFalse(self.target_path.exists())
        stash.prime()
        self.assertTrue(self.target_path.is_dir())
        self._create_factory()
        nstash: Stash = self.fac('robust')
        self.assertNotEqual(id(nstash), id(stash))
        ds_path: Path = stash.delegate.path
        for key in keys:
            path = ds_path / f'{key}.dat'
            path.unlink()
        self.assertEqual(n_missing, len(tuple(ds_path.iterdir())))
        self.assertEqual(n_missing, len(stash.delegate))
        nstash.invalidate()
        self.assertEqual(init_len, len(nstash))

    def _test_multi_create_missing(self, fn, should_missing,
                                   stash_sec='robust'):
        keys: List[str] = ' 3 5 6'.split()
        stash: Stash = self.fac(stash_sec)
        init_len: int = stash.factory.n
        n_missing: int = init_len - len(keys)
        self.assertEqual(MultiProcessRobustStash, type(stash))
        self.assertFalse(self.target_path.exists())
        stash.prime()
        self.assertTrue(self.target_path.is_dir())
        ds_path: Path = stash.delegate.path
        for key in keys:
            path = ds_path / f'{key}.dat'
            path.unlink()
        self.assertEqual(n_missing, len(tuple(ds_path.iterdir())))
        self.assertEqual(n_missing, len(stash.delegate))

        self._create_factory()
        nstash: Stash = self.fac(stash_sec)
        self.assertNotEqual(id(nstash), id(stash))
        self.assertEqual(n_missing, len(tuple(ds_path.iterdir())))
        fn(nstash)
        if should_missing:
            should_size = n_missing
        else:
            should_size = init_len
        self.assertEqual(should_size, len(nstash))
        self.assertEqual(should_size, len(tuple(ds_path.iterdir())))

    def test_multicreate_missing_len(self):
        def test_fn(stash):
            len(stash)
        self._test_multi_create_missing(test_fn, False)

    def test_multicreate_missing_load(self):
        def test_fn(stash):
            self.assertEqual('5', stash.load('5')['name'])
        self._test_multi_create_missing(test_fn, False)

    def _test_fail(self, stash: Stash):
        self.assertTrue(isinstance(stash.factory.fails, Set))
        fail_keys: Set[str] = stash.factory.fails
        self.assertTrue(len(fail_keys) > 0)
        self.assertEqual(stash.factory.n, len(stash))
        for k in fail_keys:
            self.assertTrue(isinstance(stash[k], Failure))
        self.assertEqual(len(fail_keys), len(tuple(stash.iterfails())))
        self.assertEqual(fail_keys, set(map(lambda t: t[0], stash.iterfails())))

    def test_fail(self):
        stash: Stash = self.fac('robust_fail')
        self._test_fail(stash)

    def test_fail_no_protect(self):
        stash: Stash = self.fac('robust_fai_no_protect')
        self.assertTrue(isinstance(stash.factory.fails, Set))
        fail_keys: Set[str] = stash.factory.fails
        self.assertTrue(len(fail_keys) > 0)
        with self.assertRaisesRegex(ValueError, '^Key .* is in fail list'):
            stash.prime()

    def test_fail_recover(self):
        stash: Stash = self.fac('robust_fail')
        fail_keys: Set[str] = set(stash.factory.fails)
        self._test_fail(stash)
        # config gets propogated to children
        self.fac.config.set_option('fails', 'eval: ()', 'fail_factory')
        # but who knows why this is needed too (maybe use parent as a worker?)
        stash.factory.fails.clear()
        self.assertEqual(fail_keys, stash.reprocess_failures())
        self.assertEqual(0, len(tuple(stash.iterfails())))
