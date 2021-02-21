from dataclasses import dataclass, field
from pathlib import Path
from zensols.config import Dictable
from zensols.cli import ActionCliFactory
from logutil import LogTestCase


@dataclass
class TestActionCli(Dictable):
    #CLI_META = {'dry_run'}

    dry_run: bool = field(default=False)
    """When given don't do anything, just act like it."""

    out_path: Path = field(default=None)
    """The output path."""

    def doit(self):
        print('in do it')


class TestActionObjectCli(LogTestCase):
    def test_cli(self):
        self.config_logging('zensols.cli')
        cli = ActionCliFactory.instance(
            'zensols.testapp', 'test-resources/test_app.conf')
        app = cli.create()
        self.assertTrue(isinstance(app, TestActionCli))
        #app.write()
