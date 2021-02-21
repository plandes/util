from pathlib import Path
from logutil import LogTestCase
from zensols.cli import Option, OptionFactory, Action, CommandLineParser


class TestArgumentParse(LogTestCase):
    def setUp(self):
        self.config_logging('zensols.cli')
        self.conf_opt = Option(
            'config', doc='the path to the configuration file', dtype=Path)
        self.test_action = Action('test', 'a test action',
                                  tuple([OptionFactory.dry_run()]))

    def Xtest_opt_create(self):
        opt = self.conf_opt
        self.assertEqual('FILE', opt.metavar)
        self.assertEqual(Path, opt.dtype)

    def test_single_help(self):
        parser = CommandLineParser(tuple([self.test_action]),
                                   tuple([OptionFactory.config_file()]))
        print('here')
        parser.write_help()

    def Xtest_parse(self):
        parser = CommandLineParser(tuple([self.test_action]))
        parser.parse(['--version'])
