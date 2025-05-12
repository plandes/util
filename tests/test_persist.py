import logging
from pathlib import Path
import shutil
import pickle
from io import BytesIO
import unittest
from zensols.persist import (
    DelegateDefaults,
    persisted,
    PersistedWork,
    PersistableContainer,
    DirectoryStash,
    IncrementKeyDirectoryStash,
    ShelveStash,
    shelve,
    OneShotFactoryStash,
    SortedStash,
    DictionaryStash,
    FileTextUtil,
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


class Raiser(object):
    def __getstate__(self):
        raise ValueError('attempt to pickle transient value')


class TransientPickleRaise(PersistableContainer):
    @property
    @persisted('_someprop', transient=True)
    def someprop(self):
        return Raiser()


class TransientPickleRaiseAttr(PersistableContainer):
    _PERSITABLE_TRANSIENT_ATTRIBUTES = {'someattr'}

    def __init__(self):
        self.someattr = Raiser()


class TransientPickleOverride(TransientPickle):
    def __setstate__(self, state):
        super().__setstate__(state)
        self.n = 40


class TestPersistWork(unittest.TestCase):
    def setUp(self):
        targdir = Path('target')
        if targdir.exists():
            shutil.rmtree(targdir)
        targdir.mkdir(exist_ok=True)
        self.targdir = targdir
        DelegateDefaults.CLASS_CHECK = True

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

    def test_pickle_transient_raise(self):
        sc = TransientPickleRaise()
        p = sc.someprop
        self.assertEqual(type(p), Raiser)
        with self.assertRaises(ValueError):
            self._freeze_thaw(p)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(type(sc2.someprop), Raiser)

    def test_pickle_transient_raise_attr(self):
        sc = TransientPickleRaiseAttr()
        with self.assertRaises(ValueError):
            self._freeze_thaw(sc.someattr)
        sc2 = self._freeze_thaw(sc)
        self.assertEqual(sc2.someattr, None)

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
        path = self.targdir
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
        file_path = path / 'tmp6.dat'
        with self.assertRaises(KeyError):
            s['tmp6']
        self.assertFalse(file_path.exists())

    def test_increment_key_directory_stash(self):
        path = self.targdir / 'ids'
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
        stash = IncrementKeyDirectoryStash(path, name='some-name')
        self.assertEqual(0, len(stash))

        key = 'a-non-conform-key'
        stash.dump(key, 'data')
        key_path = path / f'some-name-{key}.dat'
        self.assertTrue(key_path.exists())
        self.assertEqual('0', stash.get_last_key())
        self.assertFalse(stash.exists('data'))

        stash.dump('newdata')
        self.assertEqual('1', stash.get_last_key())
        key_path = path / 'some-name-1.dat'
        self.assertEqual(1, len(stash))
        self.assertTrue(key_path.exists())
        self.assertEqual('newdata', stash.load())

        stash = IncrementKeyDirectoryStash(path, name='some-name')
        self.assertEqual('1', stash.get_last_key())
        self.assertEqual('newdata', stash.load())

        stash.dump('yetmoredata')
        self.assertEqual(2, len(stash))
        self.assertEqual(2, len(tuple(stash.values())))
        self.assertEqual(2, len(tuple(stash.keys())))
        self.assertEqual('2', stash.get_last_key())
        self.assertEqual('yetmoredata', stash.load())

    def paths(self, name):
        ext = ShelveStash.get_extension()
        ext = '' if ext is None else f'.{ext}'
        path = self.targdir / f'{name}'
        file_path = self.targdir / f'{name}{ext}'
        return file_path, path

    def test_shelve_stash(self):
        file_path, path = self.paths('tmp6')
        s = ShelveStash(path)
        self.assertFalse(file_path.exists())
        obj = 'obj create of tmp6'
        self.assertEqual(None, s.load('tmp6'))
        self.assertTrue(file_path.exists(), f'does not exist: {file_path}')
        s.dump('tmp6', obj)
        self.assertTrue(file_path.exists())
        o2 = s.load('tmp6')
        self.assertEqual(obj, o2)
        s.delete('tmp6')
        self.assertFalse(s.exists('tmp6'))
        s.clear()
        self.assertFalse(file_path.exists())

    def test_shelve_stash_with(self):
        file_path, path = self.paths('tmp7')
        self.assertFalse(file_path.exists())
        with shelve(path) as s:
            self.assertFalse(s.exists('cool'))
        self.assertTrue(file_path.exists(), f'does not exist: {file_path}')
        with shelve(path) as s:
            s.dump('cool', [1, 2, 123])
            self.assertTrue([1, 2, 123], s.load('cool'))
        with shelve(path) as s:
            self.assertTrue([1, 2, 123], s.load('cool'))

    def _test_sorted_lexical(self, delegate, ordered, sort_fn):
        data = (('2', '6'), ('100', '1'), ('10', '2'), ('32', '4'), ('3', '5'))
        stash = OneShotFactoryStash(delegate)
        stash.worker = data
        if ordered:
            self.assertEqual(('2', '100', '10', '32', '3'), tuple(stash.keys()))
            self.assertEqual(('6', '1', '2', '4', '5'), tuple(stash.values()))
            self.assertEqual(data, tuple(stash))
        sorted_keys = ('10', '100', '2', '3', '32')
        sort_stash = SortedStash(stash, sort_function=sort_fn)
        self.assertEqual(sorted_keys, tuple(sort_stash.keys()))
        sorted_values = ('2', '1', '6', '5', '4')
        self.assertEqual(sorted_values, tuple(sort_stash.values()))
        sorted_data = (('10', '2'), ('100', '1'), ('2', '6'), ('3', '5'), ('32', '4'))
        self.assertEqual(sorted_data, tuple(sort_stash))

    def _test_sorted_numeric(self, delegate, ordered, sort_fn):
        data = (('2', '6'), ('100', '1'), ('10', '2'), ('32', '4'), ('3', '5'))
        stash = OneShotFactoryStash(delegate)
        stash.worker = data
        if ordered:
            self.assertEqual(('2', '100', '10', '32', '3'), tuple(stash.keys()))
            self.assertEqual(('6', '1', '2', '4', '5'), tuple(stash.values()))
            self.assertEqual(data, tuple(stash))
        sorted_keys = ('2', '3', '10', '32', '100')
        sort_stash = SortedStash(stash, sort_function=sort_fn)
        self.assertEqual(sorted_keys, tuple(sort_stash.keys()))
        sorted_values = ('6', '5', '2', '4', '1')
        self.assertEqual(sorted_values, tuple(sort_stash.values()))
        sorted_data = (('2', '6'), ('3', '5'), ('10', '2'), ('32', '4'), ('100', '1'))
        self.assertEqual(sorted_data, tuple(sort_stash))

    def test_sorted_dictionary(self):
        self._test_sorted_lexical(DictionaryStash(), True, None)
        path = Path('target/tmp8.dat')
        self._test_sorted_lexical(DirectoryStash(path), False, None)

        self._test_sorted_numeric(DictionaryStash(), True, int)
        path = Path('target/tmp9.dat')
        self._test_sorted_numeric(DirectoryStash(path), False, int)

        self._test_sorted_numeric(DictionaryStash(), True, float)
        path = Path('target/tmp10.dat')
        self._test_sorted_numeric(DirectoryStash(path), False, float)


class TestFileText(unittest.TestCase):
    def test_norm_name(self):
        norm = FileTextUtil.normalize_text('Test of File! Text@ Util')
        self.assertEqual('test-of-file-text-util', norm)
        norm = FileTextUtil.normalize_text('^first Test of File! Text@ Util.')
        self.assertEqual('first-test-of-file-text-util', norm)
        norm = FileTextUtil.normalize_text('Test of File! Text@ Util Last%')
        self.assertEqual('test-of-file-text-util-last', norm)
        norm = FileTextUtil.normalize_text('!--Test middle!@#$%^&*(){} Last!%')
        self.assertEqual('test-middle-last', norm)

    def test_norm_path(self):
        path = FileTextUtil.normalize_path(Path('/usr/local/bin/script.txt'))
        self.assertTrue(isinstance(path, Path))
        self.assertEqual('/usr/local/bin/script-txt', str(path))
        self.assertEqual(('/', 'usr', 'local', 'bin', 'script-txt'), path.parts)

        path = FileTextUtil.normalize_path(Path('bin/script.txt'))
        self.assertEqual(('bin', 'script-txt'), path.parts)
        self.assertEqual('bin/script-txt', str(path))

        path = FileTextUtil.normalize_path(Path('local.bin/script.txt'))
        self.assertEqual(('local-bin', 'script-txt'), path.parts)
        self.assertEqual('local-bin/script-txt', str(path))

        path = FileTextUtil.normalize_path(Path('~/src/file.c'))
        self.assertEqual(('~', 'src', 'file-c'), path.parts)
        self.assertEqual('~/src/file-c', str(path))
