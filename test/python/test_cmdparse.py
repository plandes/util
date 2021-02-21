from io import StringIO
from pathlib import Path
from logutil import LogTestCase
from zensols.cli import (
    OptionMetaData, PositionalMetaData, ActionMetaData, OptionFactory,
    Action, CommandLineParser
)


class TestArgumentParse(LogTestCase):
    def setUp(self):
        self.config_logging('zensols.cli')
        self.conf_opt = OptionFactory.config_file()
        self.dry_opt = OptionFactory.dry_run()
        self.test_action = ActionMetaData(
            'test', 'a test action', tuple([self.dry_opt]))
        self.test_action2 = ActionMetaData(
            'testmore', 'a second test action',
            positional=[PositionalMetaData('file')])

    def test_opt_create(self):
        opt = self.conf_opt
        self.assertEqual('FILE', opt.metavar)
        self.assertEqual(Path, opt.dtype)
        opt = self.conf_opt.create_option()
        self.assertEqual('FILE', opt.metavar)
        self.assertEqual('string', opt.type)
        self.assertEqual(['--config'], opt._long_opts)
        self.assertEqual(['-c'], opt._short_opts)
        opt = self.dry_opt.create_option()
        self.assertEqual(None, opt.metavar)
        self.assertEqual(None, opt.type)
        self.assertEqual(('NO', 'DEFAULT'), opt.default)
        opt = OptionFactory.dry_run(default=True).create_option()
        self.assertEqual(True, opt.default)
        opt = OptionFactory.dry_run(default=False).create_option()
        self.assertEqual(False, opt.default)

    def test_single_help(self):
        should = """\
Usage: python -m unittest [options]:

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c FILE, --config=FILE
                        the path to the config file
  -d, --dry_run         don't do anything; just act like it
"""
        parser = CommandLineParser(tuple([self.test_action]),
                                   tuple([OptionFactory.config_file()]))
        sio = StringIO()
        parser.write_help(writer=sio)
        self.assertEqual(should, sio.getvalue())

        should = """\
Usage: python -m unittest <test|testmore> [options]:

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c FILE, --config=FILE
                        the path to the config file

Actions:
test                a test action
  -d, --dry_run    don't do anything; just act like it

testmore <file>     a second test action
"""
        parser = CommandLineParser(tuple([self.test_action, self.test_action2]),
                                   tuple([OptionFactory.config_file()]))
        sio = StringIO()
        parser.write_help(writer=sio)
        self.assertEqual(should, sio.getvalue())

    def test_parse(self):
        test_action = self.test_action
        parser = CommandLineParser(tuple([test_action]))
        action: Action = parser.parse([])
        self.assertEqual(Action, type(action))
        self.assertEqual(0, len(action.positional))
        self.assertEqual({'dry_run': None}, action.options)

        action: Action = parser.parse(['-d'])
        self.assertEqual({'dry_run': True}, action.options)

        test_action = ActionMetaData(
            'test', 'a test action',
            tuple([OptionFactory.dry_run(default=True)]))
        parser = CommandLineParser(tuple([test_action]))
        action: Action = parser.parse(['-d'])
        self.assertEqual({'dry_run': False}, action.options)

    def test(self):
        self.test_action = ActionMetaData(
            'test', 'a test action', tuple([OptionFactory.dry_run()]))
