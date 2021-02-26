from io import StringIO
from pathlib import Path
from logutil import LogTestCase
from zensols.cli import (
    OptionMetaData, PositionalMetaData, ActionMetaData, OptionFactory,
    CommandAction, CommandActionSet,
    CommandLineError, CommandLineConfig, CommandLineParser
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
        self.log_action = ActionMetaData(
            'whine', 'set the logging level for the program',
            tuple([OptionFactory.whine_level()]), first_pass=True)
        self.config_action = ActionMetaData(
            'config', 'configure the application',
            tuple([OptionFactory.config_file()]), first_pass=True)

    def _complex_actions(self, n_kwargs={}) -> CommandLineParser:
        show_action = ActionMetaData('show', 'print configuration',
                                     tuple([self.dry_opt, self.conf_opt]))
        n_op = OptionMetaData('numres', 'n', dtype=int,
                              doc='the number of results', **n_kwargs)
        res_action = ActionMetaData('results', 'a test action',
                                    (self.dry_opt, n_op))
        mix_action = ActionMetaData(
            'env', 'print environment',
            (self.dry_opt, n_op),
            positional=[PositionalMetaData('section', Path)])
        return show_action, res_action, self.test_action2, mix_action

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

A test action.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d, --dry_run         don't do anything; just act like it
  -c FILE, --config=FILE
                        the path to the config file
"""
        parser = CommandLineParser(CommandLineConfig(actions=(self.test_action, self.config_action)))
        sio = StringIO()
        parser.write_help(writer=sio)
        should_lines = sorted(should.split('\n'))
        val_lines = sorted(sio.getvalue().split('\n'))
        if 0:
            print()
            print(should)
            print('-' * 80)
            print(sio.getvalue())
            print('-' * 80)
        # each run reorders the -d and -c options--so it must use a dict
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
        parser = CommandLineParser(CommandLineConfig(
            tuple([self.config_action, self.test_action, self.test_action2])))
        sio = StringIO()
        parser.write_help(writer=sio)
        self.assertEqual(should, sio.getvalue())

    def test_parse_basic(self):
        test_action = self.test_action
        parser = CommandLineParser(CommandLineConfig(tuple([test_action])))
        action_set: CommandActionSet = parser.parse([])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual(CommandAction, type(action))
        self.assertEqual(0, len(action.positional))

    def test_parse_option(self):
        test_action = self.test_action
        parser = CommandLineParser(CommandLineConfig(tuple([test_action])))
        action_set: CommandActionSet = parser.parse([])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('test', action.name)
        self.assertEqual({'dry_run': None}, action.options)
        self.assertEqual((), action.positional)

        action_set: CommandActionSet = parser.parse(['-d'])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual({'dry_run': True}, action.options)
        self.assertEqual((), action.positional)

        test_action = ActionMetaData(
            'test', 'a test action',
            tuple([OptionFactory.dry_run(default=True)]))
        parser = CommandLineParser(CommandLineConfig(tuple([test_action])))
        action_set: CommandActionSet = parser.parse([])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual({'dry_run': True}, action.options)
        self.assertEqual((), action.positional)
        action_set: CommandActionSet = parser.parse(['-d'])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual({'dry_run': False}, action.options)
        self.assertEqual((), action.positional)

    def test_parse_position(self):
        parser = CommandLineParser(CommandLineConfig((self.test_action,)))
        with self.assertRaisesRegex(CommandLineError, r"^action 'test' expects 0.*"):
            parser.parse(['test'])
        parser = CommandLineParser(CommandLineConfig((self.test_action, self.test_action2)))
        with self.assertRaisesRegex(CommandLineError, r'^no action given$'):
            parser.parse([])
        parser = CommandLineParser(CommandLineConfig((self.test_action, self.test_action2)))
        action_set: CommandActionSet = parser.parse(['test'])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('test', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None}, action.options)
        action_set: CommandActionSet = parser.parse('test -d'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('test', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': True}, action.options)
        action_set: CommandActionSet = parser.parse('prconfig a.txt'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('prconfig', action.name)
        self.assertEqual(1, len(action.positional))
        self.assertEqual(Path('a.txt'), action.positional[0])

    def test_parse_op_pos(self):
        parser = CommandLineParser(CommandLineConfig(self._complex_actions()))
        action_set: CommandActionSet = parser.parse(['results'])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('results', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': None}, action.options)
        action_set: CommandActionSet = parser.parse('results -n 1234'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('results', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 1234}, action.options)
        action_set: CommandActionSet = parser.parse('results -n 1234 -d'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('results', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': True, 'numres': 1234}, action.options)

        action_set: CommandActionSet = parser.parse('prconfig b.txt'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('prconfig', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({}, action.options)

        parser = CommandLineParser(CommandLineConfig(self._complex_actions({'default': 14})))
        action_set: CommandActionSet = parser.parse(['results'])
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('results', action.name)
        self.assertEqual((), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 14}, action.options)

    def test_parse_mix(self):
        parser = CommandLineParser(CommandLineConfig(self._complex_actions()))
        action_set: CommandActionSet = parser.parse('env b.txt'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': None, 'numres': None}, action.options)

        action_set: CommandActionSet = parser.parse('env b.txt -n 14'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 14}, action.options)

        action_set: CommandActionSet = parser.parse('env b.txt -n 14 -d'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': True, 'numres': 14}, action.options)

        action_set: CommandActionSet = parser.parse('env b.txt -d -n 15'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': True, 'numres': 15}, action.options)

        action_set: CommandActionSet = parser.parse('env -n 16 b.txt'.split())
        self.assertEqual(1, len(action_set))
        self.assertEqual(0, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': None, 'numres': 16}, action.options)

    def test_first_pass(self):
        parser = CommandLineParser(CommandLineConfig((self.test_action, self.log_action)))
        actions: CommandActionSet = parser.parse('-w 2'.split())
        self.assertEqual(2, len(actions))
        action = actions.second_pass_action
        self.assertEqual('test', action.name)
        self.assertEqual(1, len(actions.first_pass_actions))
        whine = actions.first_pass_actions[0]
        self.assertEqual(CommandAction, type(whine))
        self.assertEqual('whine', whine.name)
        self.assertEqual({'whine': 2}, whine.options)

    def test_first_pass_options(self):
        parser = CommandLineParser(CommandLineConfig((self.test_action2, self.log_action)))
        actions: CommandActionSet = parser.parse('-w 2 b.txt'.split())
        self.assertEqual(2, len(actions))
        action = actions.second_pass_action
        self.assertEqual('prconfig', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({}, action.options)
        self.assertEqual(1, len(actions.first_pass_actions))
        whine = actions.first_pass_actions[0]
        self.assertEqual(CommandAction, type(whine))
        self.assertEqual('whine', whine.name)
        self.assertEqual({'whine': 2}, whine.options)

        test_action2 = ActionMetaData(
            'prconfig', 'a second test action',
            positional=[PositionalMetaData('file', Path)],
            options=[self.conf_opt])
        parser = CommandLineParser(CommandLineConfig((test_action2, self.log_action)))
        actions: CommandActionSet = parser.parse('-w 2 b.txt -c c.conf'.split())
        self.assertEqual(2, len(actions))
        action = actions.second_pass_action
        self.assertEqual('prconfig', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'config': 'c.conf'}, action.options)
        self.assertEqual(1, len(actions.first_pass_actions))
        whine = actions.first_pass_actions[0]
        self.assertEqual(CommandAction, type(whine))
        self.assertEqual('whine', whine.name)
        self.assertEqual({'whine': 2}, whine.options)

    def test_first_pass_complex(self):
        # skip the show_action since it has a config option at the second pass
        # level
        actions = list(self._complex_actions()[1:]) + [self.config_action]
        parser = CommandLineParser(CommandLineConfig(tuple(actions)))
        action_set: CommandActionSet = parser.parse('env b.txt'.split())
        self.assertEqual(2, len(action_set))
        self.assertEqual(1, len(action_set.first_pass_actions))
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': None, 'numres': None}, action.options)

        action_set: CommandActionSet = parser.parse('env b.txt -c c.conf'.split())
        self.assertEqual(2, len(action_set))
        self.assertEqual(1, len(action_set.first_pass_actions))
        action: CommandAction = action_set.first_pass_actions[0]
        self.assertEqual('config', action.name)
        self.assertEqual({'config': 'c.conf'}, action.options)
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': None, 'numres': None}, action.options)

        action_set: CommandActionSet = parser.parse('env b.txt -c c.conf -d -n 18'.split())
        self.assertEqual(2, len(action_set))
        self.assertEqual(1, len(action_set.first_pass_actions))
        action: CommandAction = action_set.first_pass_actions[0]
        self.assertEqual('config', action.name)
        self.assertEqual({'config': 'c.conf'}, action.options)
        action: CommandAction = action_set.second_pass_action
        self.assertEqual('env', action.name)
        self.assertEqual((Path('b.txt'),), action.positional)
        self.assertEqual({'dry_run': True, 'numres': 18}, action.options)

        with self.assertRaisesRegex(CommandLineError, '^no action given$'):
            parser.parse('-c c.conf'.split())
