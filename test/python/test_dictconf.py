import unittest
import copy as cp
import yaml
import json
from io import StringIO
from zensols.config import DictionaryConfig, YamlConfig, JsonConfig


class _TestTreeConfig(object):
    def _mock_data(self):
        return {'sec1': {'k1': 'v1'},
                'sec2': {'k1': {'d1': 'v1'}}}

    def _test_eq(self, mod_fn, deep):
        ad = self._mock_data()
        bd = cp.deepcopy(ad)
        cd = cp.deepcopy(ad)

        mod_fn(cd)

        self.assertEqual(ad, bd)
        self.assertNotEqual(ad, cd)
        self.assertNotEqual(bd, cd)

        a = self._create_config(ad, deep)
        b = self._create_config(bd, deep)
        c = self._create_config(cd, deep)
        self.assertNotEqual(id(a.config), id(b.config))
        self.assertEqual(a.asdict(), b.asdict())
        self.assertNotEqual(a.asdict(), c.asdict())
        self.assertEqual(a.config, b.config)
        self.assertNotEqual(a.config, c.config)

        # paranoia
        self.assertEqual(str(ad), str(bd))
        self.assertNotEqual(str(ad), str(cd))
        self.assertEqual(str(a.asdict()), str(b.asdict()))
        self.assertNotEqual(str(a.asdict()), str(c.asdict()))
        self.assertEqual(str(a.config), str(b.config))
        self.assertNotEqual(str(a.config), str(c.config))

    def _mod_fn_shallow(self, dct):
        dct['sec1']['k1'] = 'diff val'

    def _mod_fn_deep(self, dct):
        dct['sec2']['k1']['d1'] = 'diff val'

    def test_eq_shallow(self):
        self._test_eq(self._mod_fn_shallow, True)
        self._test_eq(self._mod_fn_shallow, False)

    def test_eq_deep(self):
        self._test_eq(self._mod_fn_deep, True)
        self._test_eq(self._mod_fn_deep, False)

    def _test_invalidate(self, mod_fn, deep):
        ad = self._mock_data()
        bd = cp.deepcopy(ad)

        a = self._create_config(ad, deep)
        b = self._create_config(bd, deep)

        self.assertNotEqual(id(a.config), id(b.config))
        self.assertEqual(a.asdict(), b.asdict())
        self.assertEqual(a.config, b.config)

        if self._check_mem:
            mod_fn(bd)
            b.invalidate()
            self.assertNotEqual(a.asdict(), b.asdict())
            self.assertNotEqual(a.config, b.config)

            b.config = cp.deepcopy(ad)

        mod_fn(b.config)
        self.assertNotEqual(a.asdict(), b.asdict())
        self.assertNotEqual(a.config, b.config)

        b.config = cp.deepcopy(ad)
        self.assertNotEqual(id(a.config), id(b.config))
        self.assertEqual(a.asdict(), b.asdict())
        self.assertEqual(a.config, b.config)

    def test_invalidate_shallow(self):
        self._test_invalidate(self._mod_fn_shallow, False)
        self._test_invalidate(self._mod_fn_shallow, True)

    def test_invalidate_deep(self):
        self._test_invalidate(self._mod_fn_deep, False)
        self._test_invalidate(self._mod_fn_deep, True)

    def _test_invalidate_secs(self, mod_fn, deep):
        ad = self._mock_data()
        bd = cp.deepcopy(ad)

        a = self._create_config(ad, deep)
        b = self._create_config(bd, deep)

        self.assertNotEqual(id(a.config), id(b.config))
        self.assertEqual(a.sections, b.sections)

        if self._check_mem:
            mod_fn(bd)
            self.assertNotEqual(a.sections, b.sections)

        b.config = cp.deepcopy(ad)
        self.assertNotEqual(id(a.config), id(b.config))
        self.assertEqual(a.sections, b.sections)

    def test_invalidate_secs(self):
        def mod_fn1(dct):
            del dct['sec1']

        def mod_fn2(dct):
            dct['sec3'] = {}

        for f in (mod_fn1, mod_fn2):
            self._test_invalidate_secs(f, False)
            self._test_invalidate_secs(f, True)

    def _test_root(self, deep):
        ad = self._mock_data()
        a = self._create_config(ad, deep=deep)
        self.assertEqual('sec1', a.root)
        if self._check_mem:
            del ad['sec1']
            self.assertEqual('sec1', a.root)
            a.invalidate()
            self.assertEqual('sec2', a.root)
            ad = self._mock_data()
            a = self._create_config(ad, deep=deep)

        del a.config['sec2']
        a.invalidate()
        self.assertEqual('sec1', a.root)

        a = self._create_config(ad, deep=deep)
        a.config = self._mock_data()
        self.assertEqual('sec1', a.root)

    def test_root(self):
        self._test_root(False)
        self._test_root(True)


class TestDictConfig(_TestTreeConfig, unittest.TestCase):
    def setUp(self):
        self._check_mem = True

    def _create_config(self, mock_data, deep):
        return DictionaryConfig(mock_data, deep)


class TestYamlConfig(_TestTreeConfig, unittest.TestCase):
    def setUp(self):
        self._check_mem = False

    def _create_config(self, mock_data, deep):
        sio = StringIO()
        yaml.dump(mock_data, sio)
        sio.seek(0)
        return YamlConfig(sio)


class TestJsonConfig(_TestTreeConfig, unittest.TestCase):
    def setUp(self):
        self._check_mem = False

    def _create_config(self, mock_data, deep):
        sio = StringIO()
        json.dump(mock_data, sio)
        sio.seek(0)
        return JsonConfig(sio, deep=deep)
