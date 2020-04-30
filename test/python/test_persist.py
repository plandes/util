import logging
from sys import platform
from pathlib import Path
import pickle
from io import BytesIO
import unittest
from zensols.persist import (
    persisted,
    PersistedWork,
    PersistableContainer,
    DirectoryStash,
    ShelveStash,
    shelve,
    FactoryStash,
    DelegateStash,
    DictionaryStash,
    CacheStash,
    ReadOnlyStash,
    Stash,
)

logger = logging.getLogger(__name__)


class SomeClass(PersistableContainer):
    def __init__(self, n):
        self.n = n
        self._sp = PersistedWork(Path('target/tmp.dat'), owner=self)

    @property
    @persisted('_sp')
    def someprop(self):
        logger.info('returning: {}'.format(self.n))
        return self.n * 2


class AnotherClass(object):
    def __init__(self, n):
        self.n = n

    @property
    @persisted('counter', Path('target/tmp2.dat'))
    def someprop(self):
        return self.n * 2


class YetAnotherClass(object):
    @persisted('counter', Path('target/tmp3.dat'))
    def get_prop(self, n):
        return n * 2


class HybridClass(object):
    def __init__(self, n):
        self.n = n
        self._counter = PersistedWork(
            Path('target/tmp4.dat'), owner=self)

    def clear(self):
        self._counter.clear()

    @property
    @persisted('_counter')
    def someprop(self):
        return self.n * 2


class HybridClassPickle(PersistableContainer):
    def __init__(self, n):
        self.n = n
        self._counter = PersistedWork(
            Path('target/tmp4.dat'), owner=self)

    def clear(self):
        self._counter.clear()

    @property
    @persisted('_counter')
    def someprop(self):
        return self.n * 2


class PropertyOnlyClass(PersistableContainer):
    def __init__(self, n):
        self.n = n

    @property
    @persisted('_someprop')
    def someprop(self):
        self.n += 10
        return self.n


class GlobalTest(object):
    def __init__(self, n):
        self.n = n

    @property
    @persisted('_someprop', cache_global=True)
    def someprop(self):
        self.n += 10
        return self.n


class GlobalTestPickle(PersistableContainer):
    def __init__(self, n):
        self.n = n

    @property
    @persisted('_someprop', cache_global=True)
    def someprop(self):
        self.n += 10
        return self.n


class TransientPickle(PersistableContainer):
    def __init__(self, n):
        self.n = n

    @property
    @persisted('_someprop', transient=True)
    def someprop(self):
        self.n += 10
        return self.n


class TransientPickleOverride(TransientPickle):
    def __setstate__(self, state):
        super(TransientPickleOverride, self).__setstate__(state)
        self.n = 40


class TestPersistWork(unittest.TestCase):
    def setUp(self):
        targdir = Path('target')
        for f in 'tmp tmp2 tmp3 tmp4 tmp5 tmp6 tmp7'.split():
            p = Path(targdir, f + '.dat')
            if p.exists():
                p.unlink()
            p = Path(targdir, f + '.db')
            if p.exists():
                p.unlink()
        targdir.mkdir(0o0755, exist_ok=True)

    def _freeze_thaw(self, o):
        bio = BytesIO()
        pickle.dump(o, bio)
        data = bio.getvalue()
        bio2 = BytesIO(data)
        return pickle.load(bio2)

    def test_class_meth(self):
        sc = SomeClass(10)
        path = Path('target/tmp.dat')
        self.assertFalse(path.exists())
        self.assertEqual(20, sc.someprop)
        self.assertTrue(path.exists())
        sc = SomeClass(5)
        self.assertEqual(20, sc.someprop)
        sc = SomeClass(8)
        sc._sp.clear()
        self.assertEqual(16, sc.someprop)

    def test_property_meth(self):
        sc = AnotherClass(10)
        path = Path('target/tmp2.dat')
        self.assertFalse(path.exists())
        self.assertEqual(20, sc.someprop)
        self.assertTrue(isinstance(sc.counter, PersistedWork))
        self.assertTrue(path.exists())
        sc = AnotherClass(5)
        self.assertEqual(20, sc.someprop)
        sc = AnotherClass(8)
        # has to create the attribute first by callling
        sc.someprop
        sc.counter.clear()
        self.assertEqual(16, sc.someprop)

    def test_getter_meth(self):
        sc = YetAnotherClass()
        path = Path('target/tmp3.dat')
        self.assertFalse(path.exists())
        self.assertEqual(20, sc.get_prop(10))
        self.assertTrue(isinstance(sc.counter, PersistedWork))
        self.assertTrue(path.exists())
        sc = YetAnotherClass()
        self.assertEqual(20, sc.get_prop(5))
        sc = YetAnotherClass()
        # has to create the attribute first by callling
        sc.get_prop()
        sc.counter.clear()
        self.assertEqual(16, sc.get_prop(8))

    def test_hybrid_meth(self):
        sc = HybridClass(10)
        path = Path('target/tmp4.dat')
        self.assertFalse(path.exists())
        self.assertEqual(20, sc.someprop)
        self.assertTrue(path.exists())
        sc = HybridClass(5)
        self.assertEqual(20, sc.someprop)
        sc = HybridClass(8)
        # has to create the attribute first by callling
        sc.someprop
        sc.clear()
        self.assertEqual(16, sc.someprop)

    def test_property_cache_only(self):
        po = PropertyOnlyClass(100)
        self.assertEqual(110, po.someprop)
        self.assertTrue(isinstance(po._someprop, PersistedWork))
        po.n = 10
        self.assertEqual(10, po.n)
        self.assertEqual(110, po.someprop)
        po._someprop.clear()
        self.assertEqual(20, po.someprop)
        po = PropertyOnlyClass(3)
        self.assertEqual(13, po.someprop)

    def test_global(self):
        gt = GlobalTest(100)
        self.assertEqual(110, gt.someprop)
        gt = GlobalTest(10)
        gt.n = 1
        self.assertEqual(110, gt.someprop)
        self.assertEqual(110, gt.someprop)

    def test_set(self):
        po = PropertyOnlyClass(5)
        self.assertEqual(15, po.someprop)
        self.assertEqual(PersistedWork, type(po._someprop))
        po._someprop.set(20)
        self.assertEqual(20, po.someprop)

    def test_pickle(self):
        sc = SomeClass(5)
        path = Path('target/tmp.dat')
        self.assertFalse(path.exists())
        self.assertEqual(10, sc.someprop)
        self.assertTrue(path.exists())
        self.assertEqual(10, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(SomeClass, type(sc2))
        self.assertEqual(10, sc2.someprop)

    def test_pickle_proponly(self):
        sc = PropertyOnlyClass(2)
        self.assertEqual(12, sc.someprop)
        self.assertEqual(12, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(PropertyOnlyClass, type(sc2))
        self.assertEqual(12, sc2.someprop)

    def test_pickle_global(self):
        sc = GlobalTestPickle(2)
        # fails because of global name collision
        self.assertEqual(12, sc.someprop)
        self.assertEqual(12, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(GlobalTestPickle, type(sc2))
        self.assertEqual(12, sc2.someprop)

    def test_pickle_hybrid(self):
        sc = HybridClassPickle(2)
        # fails because of global name collision
        self.assertEqual(4, sc.someprop)
        self.assertEqual(4, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(HybridClassPickle, type(sc2))
        self.assertEqual(4, sc2.someprop)

    def test_pickle_transient(self):
        sc = TransientPickle(10)
        sc.n = 2
        # fails because of global name collision
        self.assertEqual(12, sc.someprop)
        self.assertEqual(12, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(TransientPickle, type(sc2))
        logger.debug('setting sc2.n')
        # should recalculate from updated value instead of hanging on to old
        sc2.n = 3
        self.assertEqual(13, sc2.someprop)

    def test_pickle_transient_override(self):
        sc = TransientPickleOverride(2)
        # fails because of global name collision
        self.assertEqual(12, sc.someprop)
        self.assertEqual(12, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(TransientPickleOverride, type(sc2))
        self.assertEqual(50, sc2.someprop)

    def test_pickle_transient_two_pass(self):
        sc = TransientPickle(10)
        sc.n = 2
        # fails because of global name collision
        self.assertEqual(12, sc.someprop)
        self.assertEqual(12, sc.someprop)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(TransientPickle, type(sc2))
        logger.debug('setting sc2.n')
        # should recalculate from updated value instead of hanging on to old
        sc2.n = 3
        self.assertEqual(13, sc2.someprop)
        sc3 = self._freeze_thaw(sc)
        sc3.n = 4
        self.assertEqual(12, sc.someprop)
        self.assertEqual(13, sc2.someprop)
        self.assertEqual(14, sc3.someprop)
        self.assertEqual(TransientPickle, type(sc3))

    def test_dir_stash(self):
        path = Path('target')
        file_path = path / 'tmp5.dat'
        s = DirectoryStash(path)
        self.assertFalse(file_path.exists())
        obj = 'obj create of tmp5'
        self.assertEqual(None, s.load('tmp5'))
        self.assertFalse(file_path.exists())
        s.dump('tmp5', obj)
        self.assertTrue(file_path.exists())
        o2 = s.load('tmp5')
        self.assertEqual(obj, o2)
        s.delete('tmp5')
        self.assertFalse(file_path.exists())

    def paths(self, name):
        path = Path('target')
        file_path = path / f'{name}.db'
        if platform == "linux" or platform == "linux2":
            path = file_path
        else:
            path = path / name
        return file_path, path

    def test_shelve_stash(self):
        file_path, path = self.paths('tmp6')
        s = ShelveStash(path)
        self.assertFalse(file_path.exists())
        obj = 'obj create of tmp6'
        self.assertEqual(None, s.load('tmp6'))
        self.assertTrue(file_path.exists())
        s.dump('tmp6', obj)
        self.assertTrue(file_path.exists())
        o2 = s.load('tmp6')
        self.assertEqual(obj, o2)
        s.delete('tmp6')
        self.assertFalse(file_path.exists())

    def test_shelve_stash_with(self):
        file_path, path = self.paths('tmp7')
        self.assertFalse(file_path.exists())
        with shelve(path) as s:
            self.assertFalse(s.exists('cool'))
        self.assertTrue(file_path.exists())
        with shelve(path) as s:
            s.dump('cool', [1, 2, 123])
            self.assertTrue([1, 2, 123], s.load('cool'))
        with shelve(path) as s:
            self.assertTrue([1, 2, 123], s.load('cool'))


class IncStash(ReadOnlyStash):
    def __init__(self):
        super(IncStash, self).__init__()
        self.c = 0

    def load(self, name: str):
        self.c += 1
        return f'{name}-{self.c}'

    def keys(self):
        return ()


class RangeStash(ReadOnlyStash):
    def __init__(self, n):
        super(Stash, self).__init__()
        self.n = n

    def load(self, name: str):
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

