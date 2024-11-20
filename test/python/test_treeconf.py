import logging
from io import StringIO
from zensols.config import (
    Settings, FactoryError, ConfigurableError,
    ImportConfigFactory, ImportIniConfig, ImportYamlConfig
)
from logutil import LogTestCase

logger = logging.getLogger(__name__)

CONFIG = """
[import]
sections = list: test_imp
[test_imp]
type = import
config_file = test-resources/treeconf/{}.yml
"""

CONFIG_DEFAULT = """
[import]
sections = list: test_imp
references = list: app_default

[test_imp]
type = import
config_file = test-resources/treeconf/{}.yml

[app_default]
is_foo_enabled = {}
"""


class TestPersistWork(LogTestCase):
    def setUp(self):
        super().setUp()
        #self.config_logging(__name__)

    def _factory(self, name: str) -> ImportConfigFactory:
        config = CONFIG.format(name)
        return ImportConfigFactory(ImportIniConfig(StringIO(config)))

    def _compare_file_config(self, fac: ImportConfigFactory,
                             is_mult: bool, has_imp: bool,):
        sec: Settings = fac('default')
        self.assertEqual({'param1': 3.14}, sec.asdict())
        fn = self.assertTrue if is_mult else self.assertFalse
        fn('other' in fac.config.sections)
        fn = self.assertTrue if has_imp else self.assertFalse
        fn('app_pkg_imp' in fac.config.sections)

    def test_files(self):
        fac: ImportConfigFactory = self._factory('multi-files')
        self._compare_file_config(fac, True, True)

    def test_files_str(self):
        fac: ImportConfigFactory = self._factory('multi-files-str')
        self._compare_file_config(fac, True, True)

    def test_single_file(self):
        fac: ImportConfigFactory = self._factory('single-file')
        self._compare_file_config(fac, False, True)

    def test_cleanup(self):
        fac: ImportConfigFactory = self._factory('cleanup-section')
        self._compare_file_config(fac, False, False)

    def test_no_files(self):
        fac: ImportConfigFactory = self._factory('no-files')
        err: str = 'Can not populate from section default'
        with self.assertRaisesRegex(FactoryError, err) as context:
            self._compare_file_config(fac, False, False)
        self.assertEqual(ConfigurableError, type(context.exception.__cause__))

    def test_extra_entries(self):
        fac: ImportConfigFactory = self._factory('extra-entries')
        err: str = 'Can not populate from section default'
        with self.assertRaisesRegex(FactoryError, err) as context:
            self._compare_file_config(fac, False, False)
        self.assertEqual(ConfigurableError, type(context.exception.__cause__))

    def test_not_enabled(self):
        config = CONFIG.format('enabled')
        fac = ImportConfigFactory(ImportIniConfig(StringIO(config)))
        self.assertEqual({'app_pkg_imp'}, fac.config.sections)

    def test_condition_enabled(self):
        config = CONFIG_DEFAULT.format('condition-enabled', 'True')
        fac = ImportConfigFactory(ImportIniConfig(StringIO(config)))
        self._compare_file_config(fac, True, False)

    def test_condition_disabled(self):
        config = CONFIG_DEFAULT.format('condition-enabled', 'False')
        config = ImportIniConfig(StringIO(config))
        self.assertEqual({'app_default:is_foo_enabled': 'False'},
                         config.as_one_tier_dict())

    def test_order_preserving(self):
        config = ImportYamlConfig('test-resources/treeconf/order-preserve.yml')
        for i, (k, v) in enumerate(config.get_options('app_pkg_imp.import').items()):
            self.assertEqual(f'pkg_imp_{i}', k)
