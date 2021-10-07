import unittest
import os
from io import StringIO, BytesIO
import pickle
from pathlib import Path
from zensols.config import StringConfig, ImportIniConfig, ConfigurableError


class TestImportConfig(unittest.TestCase):
    def setUp(self):
        os.environ['FAKEVAR_DOT'] = '.'
        self.cconf = StringConfig('nasc.test_impconfig_app_root=.')
        self.conf = ImportIniConfig('test-resources/import-config-test.conf',
                                    children=[self.cconf],
                                    exclude_config_sections=False)

    def test_config(self):
        conf = self.conf
        self.assertEqual('this is a cool test', conf.get_option('text', 'sec1'))
        self.assertEqual('imported firstval', conf.get_option('text', 'sec2'))
        self.assertEqual('local import of a greek letter', conf.get_option('text', 'sec3'))
        self.assertEqual('path: test-resources/test.json', conf.get_option('text', 'sec4'))
        jconf = conf.populate(section='sec4')
        path = jconf.text
        self.assertTrue(isinstance(path, Path))

    def test_env(self):
        conf = self.conf
        key = 'unittest.test_impconfig_val'
        testval = 'testval'
        os.environ[key] = testval
        self.assertEqual(testval, conf.get_option(key, 'ev'))

    def test_child_ref(self):
        self.assertEqual('two way for this: grabbed parents param1, which is cool',
                         self.conf.get_option('text', 'sec5'))

    def test_config_interpolate(self):
        conf = self.conf
        self.assertEqual('./test-resources/config-write.conf',
                         conf.get_option('config_file', 'import_ini1'))

    def test_config_sections(self):
        conf = self.conf
        should = set(('nasc import imp_def_sec empty import_ini1 import_str2 ' +
                      'import_a_json sec1 sec2 sec3 sec4 temp1 temp2 grk ' +
                      'jsec_1 jsec_2 imp_env ev impref sec5 sec6 need_vars').split())
        self.assertEqual(should, set(conf.sections))
        conf = ImportIniConfig('test-resources/import-config-test.conf',
                               children=[self.cconf])
        should = should - set('import import_ini1 import_a_json impref imp_env import_str2'.split())
        self.assertEqual(should, set(conf.sections))

    def test_env_section(self):
        conf = self.conf
        self.assertEqual('dot: <.>', conf.get_option('text', 'sec6'))

    def test_picke(self):
        sio = StringIO()
        self.conf.write(writer=sio)
        bio = BytesIO()
        pickle.dump(self.conf, bio)
        bio.seek(0)
        unp = pickle.load(bio)
        sio_unp = StringIO()
        unp.write(writer=sio_unp)
        self.assertEqual(sio.getvalue(), sio_unp.getvalue())

    def test_bad_property(self):
        self.conf = ImportIniConfig('test-resources/import-config-bad-sec.conf')
        with self.assertRaisesRegex(ConfigurableError, r"^Invalid options in section 'import"):
            self.conf.sections

    def test_multiconfig(self):
        self.conf = ImportIniConfig('test-resources/import-config-multi-config.conf')
        with self.assertRaisesRegex(ConfigurableError, r"^Cannot have both 'config_file' and 'config_files' in section 'import' in file"):
            self.conf.sections
