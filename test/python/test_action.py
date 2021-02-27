from typing import Dict
from zensols.cli import (
    ActionCli, ActionCliManager,
    OptionMetaData, ActionMetaData,
    CommandActionSet, ApplicationFactory, Application, ApplicationResult,
)
from logutil import LogTestCase
import mockapp.log as ml
import mockapp.app as ma


class TestActionSecondPass(LogTestCase):
    def setUp(self):
        #self.config_logging('zensols.cli')
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-sec-pass.conf')

    def test_metadata(self):
        if 0:
            print()
            self.cli.parser.write_help()
        mng: ActionCliManager = self.cli.cli_manager
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
        self.assertEqual(ml.LogLevel, opt.dtype)
        self.assertEqual(ml.LogLevel.info, opt.default)
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
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-first-pass.conf')

    def test_metadata(self):
        if 0:
            print()
            self.cli.parser.write_help()
        mng: ActionCliManager = self.cli.cli_manager
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
        self.assertEqual(ml.LogLevel, opt.dtype)
        self.assertEqual(ml.LogLevel.info, opt.default)
        op_opt = opt.create_option()
        self.assertEqual(['--level'], op_opt._long_opts)
        self.assertEqual(['-e'], op_opt._short_opts)
        self.assertEqual('choice', op_opt.type)
        self.assertEqual(tuple('debug error info warning'.split()), op_opt.choices)
        self.assertEqual('info', op_opt.default)
        opt: OptionMetaData = meta.options_by_name['defaultlevel']
        self.assertEqual('f', opt.short_name)
        self.assertEqual('the level to set the root logger', opt.doc)
        TestActionSecondPass._test_second_action(self, actions)


class TestActionInvoke(LogTestCase):
    def setUp(self):
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-first-pass.conf')

    def test_construct(self):
        #self.config_logging('zensols.cli')
        if 0:
            print()
            self.cli.parser.write_help()
        aset: CommandActionSet = self.cli.create('one 2 -g 5 -e debug'.split())
        #aset.write()
        #self.config_logging('zensols.cli')
        insts = aset.invoke()
        self.assertEqual(2, len(insts))
        res: Application = insts[0]
        self.assertEqual(ApplicationResult, type(res))
        self.assertTrue(isinstance(res.instance, ml.LogConfigurator))
        res: Application = insts[1]
        self.assertTrue(isinstance(res.instance, ma.TestAction))
        self.assertEqual((5, 2.0, 5, 'str1x'), res.instance.invoke_state)
        self.assertEqual((5, 2.0, 5, 'str1x', 'r'), res.result)
