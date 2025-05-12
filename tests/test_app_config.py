from typing import Any
from dataclasses import dataclass
import sys
from io import StringIO
from pathlib import Path
from zensols.util import stdwrite
from zensols.introspect import IntegerSelection, Kind
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


CONFIG_METH = """\
[cli]
apps = list: app
cleanups = list: app, cli
usage_config = object({'param': {'width': 80}}): zensols.cli.UsageConfig

[app]
class_name = test_app_config.App2
"""


@dataclass
class App(object):
    val1: str

    def run(self):
        return self.val1


@dataclass
class App2(object):
    """Application doc.

    """
    def meth1(self):
        """No-op method."""
        return 'noop'

    def meth2(self, fv: int, sv: int = 5):
        """Invoke a test method.

        :param fv: first param

        :param sv: second param

        """
        return [fv, sv]

    def meth3(self, input_file: Path = Path('a-default.txt')):
        """Invoke a test method with a path default.

        :param input_file: the input file

        """
        return input_file

    def meth4(self, isel: IntegerSelection = IntegerSelection('0')):
        """Invoke an int selection method.

        isel: the integer selection

        """
        return isel


class BarfApplicationFactory(ApplicationFactory):
    def _handle_error(self, ex: Exception):
        raise ex


class TestArgumentParse(LogTestCase):
    def _test_config_param(self, config: str, name: str, should: Any):
        harness = CliHarness(
            app_factory_class=BarfApplicationFactory,
            package_resource='zensols.util',
            app_config_resource=StringIO(config))
        res: ActionResult = harness.execute(
            ['-c', f'test-resources/app-config/{name}.conf'])
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


class TestIntegerSel(LogTestCase):
    def test_parse(self):
        arr = list(range(1, 10))

        i = IntegerSelection('3')
        self.assertEqual(3, i.selection)
        self.assertEqual((3,), tuple(i))
        self.assertEqual(Kind.single, i.kind)
        self.assertEqual([4], i.select(arr))

        i = IntegerSelection('3,4')
        self.assertEqual([3, 4], i.selection)
        self.assertEqual((3, 4,), tuple(i))
        self.assertEqual(Kind.list, i.kind)
        self.assertEqual([4, 5], i.select(arr))

        i = IntegerSelection('3,4,5')
        self.assertEqual([3, 4, 5], i.selection)
        self.assertEqual((3, 4, 5), tuple(i))
        self.assertEqual(Kind.list, i.kind)
        self.assertEqual([4, 5, 6], i.select(arr))
        self.assertEqual((3, 4, 5), tuple(i))

        i = IntegerSelection('3:4')
        self.assertEqual((3, 4), i.selection)
        self.assertEqual((3, 4), tuple(i))
        self.assertEqual(Kind.interval, i.kind)
        self.assertEqual([4], i(arr))

        i = IntegerSelection('3:5')
        self.assertEqual((3, 5), i.selection)
        self.assertEqual((3, 4, 5), tuple(i))
        self.assertEqual(Kind.interval, i.kind)
        self.assertEqual([4, 5], i(arr))

        i = IntegerSelection('-1')
        self.assertEqual(-1, i.selection)
        self.assertEqual((-1,), tuple(i))
        self.assertEqual(Kind.single, i.kind)
        self.assertEqual([9], i(arr))


class TestMethodParse(LogTestCase):
    def setUp(self):
        self.harness = CliHarness(
            package_resource='zensols.util',
            app_config_resource=StringIO(CONFIG_METH))
        self.maxDiff = sys.maxsize

    def _test_meth_primitive(self):
        harness = self.harness
        res: ActionResult = harness.execute('meth1')
        self.assertEqual('noop', res.result)

        res: ActionResult = harness.execute('meth2 1')
        self.assertEqual([1, 5], res.result)

        res: ActionResult = harness.execute('meth2 1 -s 2')
        self.assertEqual([1, 2], res.result)

        res: ActionResult = harness.execute('meth2 1 --sv 2')
        self.assertEqual([1, 2], res.result)

        res: ActionResult = harness.execute('meth2 1 --sv 2')
        self.assertEqual([1, 2], res.result)

    def _test_path(self):
        harness = self.harness
        res: ActionResult = harness.execute('meth3')
        self.assertEqual(Path('a-default.txt'), res.result)

        res: ActionResult = harness.execute('meth3 -i a.txt')
        self.assertEqual(Path('a.txt'), res.result)

        res: ActionResult = harness.execute('meth3 --inputfile b.txt')
        self.assertEqual(Path('b.txt'), res.result)

    def test_long_help(self):
        sio = StringIO()
        with stdwrite(stdout=sio, stderr=sio):
            self.harness.execute('--help')
        if False:
            print(f'should = <{sio.getvalue()}>')
            return
        should = """\
Usage: python -m unittest <meth1|meth2|meth3|meth4> [options]:

Application doc.

Options:
  -h, --help [actions]                    show this help message and exit
  --version                               show the program version and exit

Actions:
meth1                                     no-op method

meth2 <fv>                                invoke a test method
  fv INT                                  first param
  -s, --sv INT               5            second param

meth3                                     invoke a test method with a path
                                          default
  -i, --inputfile FILE       a-defaul...  the input file with default
                                          a-default.txt

meth4                                     invoke an int selection method. isel:
                                          the integer selection
  -e, --isel INT[,INT|:INT]  0
exit: 0\n"""
        self.assertEqual(should, sio.getvalue())

    def test_short_help(self):
        sio = StringIO()
        with stdwrite(stdout=sio, stderr=sio):
            self.harness.execute('-h')
        if False:
            print()
            print(f'should = <{sio.getvalue()}>')
            return
        should = """\
Usage: python -m unittest [-h|--help] [--version]
       python -m unittest <action> [action options]
       python -m unittest meth1
       python -m unittest meth2 <fv> [-s INT]
       python -m unittest meth3 [-i FILE]
       python -m unittest meth4 [-e INT[,INT|:INT]]
exit: 0\n"""
        self.assertEqual(should, sio.getvalue())

    def test_integer_selection(self):
        harness = self.harness
        res: ActionResult = harness.execute('meth4')
        self.assertTrue(isinstance(res.result, IntegerSelection))
        self.assertEqual(0, res.result.selection)
        self.assertEqual(Kind.single, res.result.kind)

        res: ActionResult = harness.execute('meth4 -e 3')
        self.assertTrue(isinstance(res.result, IntegerSelection))
        self.assertEqual(3, res.result.selection)
        self.assertEqual(Kind.single, res.result.kind)

        res: ActionResult = harness.execute('meth4 --isel 3,4')
        self.assertTrue(isinstance(res.result, IntegerSelection))
        self.assertEqual([3, 4], res.result.selection)
        self.assertEqual(Kind.list, res.result.kind)

        res: ActionResult = harness.execute('meth4 --isel 3,4,5')
        self.assertTrue(isinstance(res.result, IntegerSelection))
        self.assertEqual([3, 4, 5], res.result.selection)
        self.assertEqual(Kind.list, res.result.kind)

        res: ActionResult = harness.execute('meth4 --isel 3:4')
        self.assertTrue(isinstance(res.result, IntegerSelection))
        self.assertEqual((3, 4), res.result.selection)
        self.assertEqual(Kind.interval, res.result.kind)
