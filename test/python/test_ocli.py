from dataclasses import dataclass, field
from pathlib import Path
from zensols.config import Dictable
from zensols.cli import CommandFactory
from logutil import LogTestCase


@dataclass
class TestAction(Dictable):
    """Test command line.

    """
    #CLI_META = {'dry_run'}

    dry_run: bool = field(default=False)
    """When given don't do anything, just act like it."""

    out_path: Path = field(default=None)
    """The output path."""

    def doit(self, a1, arg0: str, arg1: int = 1, arg2: str = 'str1x'):
        """Run the test
        command

        in the unit test

        :param a1: first arg doc

        :param arg0: second arg doc

        :param arg1: third arg
                     doc

        :param arg2: forth arg doc

        """
        print('in do it:', arg1)


class TestActionObjectCli(LogTestCase):
    def test_cli(self):
        self.config_logging('zensols.cli')
        cli = CommandFactory.instance(
            'zensols.testapp', 'test-resources/test-app.conf')
        command = cli.create()
        command.parser.write_help()
