from io import StringIO
from pathlib import Path
from logutil import LogTestCase
from zensols.cli import (
    OptionMetaData, PositionalMetaData, ActionMetaData, OptionFactory,
    CommandLineError, Action, CommandLineParser
)


class TestArgumentParse(LogTestCase):
    def setUp(self):
        #self.config_logging('zensols.cli')
        self.conf_opt = OptionFactory.config_file()
        self.dry_opt = OptionFactory.dry_run()
        self.test_action = ActionMetaData(
            'test', 'a test action', tuple([self.dry_opt]))
        self.test_action2 = ActionMetaData(
            'prconfig', 'a second test action',
            positional=[PositionalMetaData('file', Path)])

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
  -d, --dry_run         don't do anything; just act like it
  -c FILE, --config=FILE
                        the path to the config file
"""
        parser = CommandLineParser(tuple([self.test_action]),
                                   tuple([OptionFactory.config_file()]))
        sio = StringIO()
        parser.write_help(writer=sio)
        should_lines = sorted(should.split('\n'))
        val_lines = sorted(sio.getvalue().split('\n'))
        # each run reorders the -d and -c options--so it must use a dict
        #self.assertEqual(should, sio.getvalue())
        self.assertEqual(should_lines, val_lines)

        should = """\
Usage: python -m unittest <prconfig|test> [options]:

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c FILE, --config=FILE
                        the path to the config file

Actions:
prconfig <file>     a second test action

test                a test action
  -d, --dry_run    don't do anything; just act like it
"""
        parser = CommandLineParser(tuple([self.test_action, self.test_action2]),
                                   tuple([OptionFactory.config_file()]))
        sio = StringIO()
        parser.write_help(writer=sio)
        self.assertEqual(should, sio.getvalue())

    def test_parse_basic(self):
        test_action = self.test_action
        parser = CommandLineParser(tuple([test_action]))
        action: Action = parser.parse([])
        self.assertEqual(Action, type(action))
        self.assertEqual(0, len(action.positional))

    def test_parse_option(self):
        test_action = self.test_action
        parser = CommandLineParser(tuple([test_action]))
        action: Action = parser.parse([])
        self.assertEqual('test', action.meta_data.name)
        self.assertEqual({'dry_run': None}, action.options)
        self.assertEqual((), action.positional)

        action: Action = parser.parse(['-d'])
        self.assertEqual({'dry_run': True}, action.options)
        self.assertEqual((), action.positional)

        test_action = ActionMetaData(
            'test', 'a test action',
            tuple([OptionFactory.dry_run(default=True)]))
        parser = CommandLineParser(tuple([test_action]))
        action: Action = parser.parse([])
        self.assertEqual({'dry_run': True}, action.options)
        self.assertEqual((), action.positional)
        action: Action = parser.parse(['-d'])
        self.assertEqual({'dry_run': False}, action.options)
        self.assertEqual((), action.positional)

    def test_parse_position(self):
        parser = CommandLineParser((self.test_action,))
        with self.assertRaisesRegex(CommandLineError, r"^action 'test' expects 0.*"):
            parser.parse(['test'])
        parser = CommandLineParser((self.test_action, self.test_action2))
        with self.assertRaisesRegex(CommandLineError, r'^no action given$'):
            parser.parse([])
        parser = CommandLineParser((self.test_action, self.test_action2))
        action: Action = parser.parse(['test'])
        self.assertEqual('test', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None}, action.options)
        action: Action = parser.parse('test -d'.split())
        self.assertEqual('test', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': True}, action.options)
        action: Action = parser.parse('prconfig a.txt'.split())
        self.assertEqual('prconfig', action.meta_data.name)
        self.assertEqual(1, len(action.positional))
        self.assertEqual(Path('a.txt'), action.positional[0])

    def _complex_actions(self, n_kwargs={}) -> CommandLineParser:
        show_action = ActionMetaData('show', 'print configuration',
                                     tuple([self.dry_opt, self.conf_opt]))
        n_op = OptionMetaData('numres', 'n', dtype=int,
                              doc='the number of results', **n_kwargs)
        res_action = ActionMetaData('results', 'a test action',
                                    (self.dry_opt, n_op))
        return show_action, res_action, self.test_action2

    def test_parse_op_pos(self):
        parser = CommandLineParser(self._complex_actions())
        action: Action = parser.parse(['results'])
        self.assertEqual('results', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': None}, action.options)
        action: Action = parser.parse('results -n 1234'.split())
        self.assertEqual('results', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 1234}, action.options)
        action: Action = parser.parse('results -n 1234 -d'.split())
        self.assertEqual('results', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': True, 'numres': 1234}, action.options)

        parser = CommandLineParser(self._complex_actions({'default': 14}))
        action: Action = parser.parse(['results'])
        self.assertEqual('results', action.meta_data.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 14}, action.options)
