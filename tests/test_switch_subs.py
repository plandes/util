from dataclasses import dataclass, field
from enum import Enum, auto
import sys
from pathlib import Path
from io import StringIO
from zensols.util import stdwrite
from zensols.cli import CliHarness, ApplicationFactory
from logutil import LogTestCase


CONFIG = """\
[cli]
apps = list: config_cli, app
cleanups = list: config_cli, app, cli

[config_cli]
class_name = zensols.cli.ConfigurationImporter

[config_imp_conf]
config_files = list: {config_path}, test-resources/app-config/1.conf

[app]
class_name = test_switch_subs.Application

[app_decorator]
option_excludes = set: config_factory
option_overrides = dict: {
  'out_format': {'long_name': 'format', 'short_name': None},
  'employee_id': {'long_name': 'empid'}}
mnemonic_overrides = dict: {
  'print_employees': 'emp',
  'process_organizations': 'org'}
"""


class Format(Enum):
    one = auto()
    two = auto()


@dataclass
class Application(object):
    """An employee database application (print using ``|prog|
    :meth:`print_employees` :obj:`dry_run```).

    """
    dry_run: bool = field()
    """Whether to execute an action."""

    def print_employees(self, out_format: Format, employee_id: int = None):
        """Show employee by ID (should not replace ``org_idd``).

        :param out_format: output format for employee with ID given by
                           ``employee_id``

        :param employee_id: the ID of the employee

        """
        pass

    def process_organizations(self, org_id: int = None):
        """Process organizations by ID or print with :obj:`dry_run` (should
        replace ``org_id``).

        :param org_id: a unique ID

        """
        pass


class TestSwitchSubs(LogTestCase):
    WRITE: bool = False

    def setUp(self):
        super().setUp()
        self.maxDiff = sys.maxsize

    def test_subs(self):
        should = Path('test-resources/should/switch-sub.txt')
        harness = CliHarness(
            app_factory_class=ApplicationFactory,
            package_resource='zensols.util',
            app_config_resource=StringIO(CONFIG))
        sio = StringIO()
        with stdwrite(stdout=sio, stderr=sio):
            harness.execute('--help')
        hstr: str = sio.getvalue()
        if self.WRITE:
            print(hstr)
            should.write_text(hstr)
        self.assertEqual(should.read_text(), hstr)
