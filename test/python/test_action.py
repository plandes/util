from typing import Dict
from dataclasses import dataclass, field
from pathlib import Path
from zensols.config import Dictable
from zensols.cli import (
    ActionCli, ActionCliManager, OptionMetaData, ActionMetaData, CommandFactory
)
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

    def doit(self, a1, arg0: float, arg1: int = 1, arg2: str = 'str1x'):
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


class TestActionSecondPass(LogTestCase):
    def setUp(self):
        #self.config_logging('zensols.cli')
        cli = CommandFactory.instance(
            'zensols.testapp', 'test-resources/test-app-sec-pass.conf')
        self.command = cli.create()

    def test_metadata(self):
        command = self.command
        if 0:
            print()
            command.parser.write_help()
        mng: ActionCliManager = command.cli_manager
        actions: Dict[str, ActionCli] = mng.actions
        self.assertEqual(2, len(actions))
        self.assertEqual(set('test log_action'.split()), set(actions.keys()))

        log = actions['log_action']
        self.assertEqual('log_action', log.section)
        metas = log.meta_datas
        self.assertEqual(1, len(metas))
        meta: ActionMetaData = metas[0]
        self.assertEqual('configlog', meta.name)
        self.assertEqual('configure the log system', meta.doc)
        self.assertEqual(2, len(meta.options))
        self.assertEqual(False, meta.first_pass)
        opt: OptionMetaData = meta.options_by_name['level']
        self.assertEqual('level', opt.long_name)
        self.assertEqual('e', opt.short_name)
        self.assertEqual('level', opt.dest)
        self.assertEqual(str, opt.dtype)
        self.assertEqual('info', opt.default)
        opt: OptionMetaData = meta.options_by_name['defaultlevel']
        self.assertEqual('f', opt.short_name)
        self.assertEqual('the level to set the root logger', opt.doc)
        self._test_second_action(self, actions)

    @staticmethod
    def _test_second_action(self, actions):
        test = actions['test']
        self.assertEqual('test', test.section)
        metas = test.meta_datas
        self.assertEqual(1, len(metas))
        meta: ActionMetaData = metas[0]
        self.assertEqual('doit', meta.name)
        self.assertEqual('run the test command in the unit test', meta.doc)
        self.assertEqual(4, len(meta.options))
        self.assertEqual(False, meta.first_pass)
        opt: OptionMetaData = meta.options_by_name['arg2']
        self.assertEqual('arg2', opt.long_name)
        self.assertEqual('2', opt.short_name)
        self.assertEqual('str1x', opt.default)
        self.assertEqual('STRING', opt.metavar)
        self.assertEqual(str, opt.dtype)
        pos = meta.positional
        self.assertEqual(2, len(pos))
        self.assertEqual('a1', pos[0].name)
        self.assertEqual(str, pos[0].dtype)
        self.assertEqual('arg0', pos[1].name)
        self.assertEqual(float, pos[1].dtype)


class TestActionFirstPass(LogTestCase):
    def setUp(self):
        #self.config_logging('zensols.cli')
        cli = CommandFactory.instance(
            'zensols.testapp', 'test-resources/test-app-first-pass.conf')
        self.command = cli.create()

    def test_metadata(self):
        command = self.command
        if 0:
            print()
            command.parser.write_help()
        mng: ActionCliManager = command.cli_manager
        actions: Dict[str, ActionCli] = mng.actions
        self.assertEqual(2, len(actions))
        self.assertEqual(set('test log_action'.split()), set(actions.keys()))

        log = actions['log_action']
        self.assertEqual('log_action', log.section)
        metas = log.meta_datas
        self.assertEqual(1, len(metas))
        meta: ActionMetaData = metas[0]
        self.assertEqual('configlog', meta.name)
        self.assertEqual('configure the log system', meta.doc)
        self.assertEqual(2, len(meta.options))
        self.assertEqual(True, meta.first_pass)
        opt: OptionMetaData = meta.options_by_name['level']
        self.assertEqual('level', opt.long_name)
        self.assertEqual('e', opt.short_name)
        self.assertEqual('level', opt.dest)
        self.assertEqual(str, opt.dtype)
        self.assertEqual('info', opt.default)
        opt: OptionMetaData = meta.options_by_name['defaultlevel']
        self.assertEqual('f', opt.short_name)
        self.assertEqual('the level to set the root logger', opt.doc)
        TestActionSecondPass._test_second_action(self, actions)
