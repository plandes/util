from typing import Any
from dataclasses import dataclass
from io import StringIO
from zensols.config import FactoryError
from zensols.cli import ActionResult, CliHarness, ApplicationFactory
from logutil import LogTestCase


CONFIG = """\
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: config_cli, app
cleanups = list: config_cli, app, cli

[config_cli]
class_name = zensols.cli.ConfigurationImporter
%(conf_cli_conf)s

[config_imp_conf]
config_files = list: {config_path}, test-resources/app-config/2.conf

[import]
sections = list: imp_env

[imp_env]
type = environment
section_name = env
includes = set: GITUSER

[app]
class_name = test_app_config.App
val1 = ${some_default_sec:val1}
"""


@dataclass
class App(object):
    val1: str

    def run(self):
        return self.val1


class BarfApplicationFactory(ApplicationFactory):
    def _handle_error(self, ex: Exception):
        raise ex


class TestArgumentParse(LogTestCase):
    def _test_config_param(self, config: str, name: str, should: Any):
        harness = CliHarness(
            app_factory_class=BarfApplicationFactory,
            package_resource='zensols.util',
            app_config_resource=StringIO(config))
        res: ActionResult = harness.invoke(
            ['_', '-c', f'test-resources/app-config/{name}.conf'])
        self.assertEqual(should, res.result)

    def test_config_nom(self):
        config = CONFIG % {'conf_cli_conf': '', 'config_files': ''}
        self._test_config_param(config, '1', 1)
        self._test_config_param(config, '2', 'val2')

    def test_bad_config_section(self):
        config = CONFIG % {'conf_cli_conf': 'extraneous_op = 3',
                           'config_files': ''}
        err = r"^Can not create 'config_cli' for class.*'extraneous_op'$"
        with self.assertRaisesRegex(FactoryError, err):
            self._test_config_param(config, '1', 1)

    def test_config_with_section(self):
        config = CONFIG % {
            'conf_cli_conf': "type=import\nsection = config_imp_conf",
            'config_files': '{config_path}, test-resources/app-config/2.conf'}
        # sections are loaded
        self._test_config_param(config, '1', 'val2')
