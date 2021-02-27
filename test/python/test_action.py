from typing import Dict
import sys
from io import StringIO
from zensols.cli import (
    ActionCli, ActionCliManager,
    OptionMetaData, ActionMetaData,
    CommandActionSet, ApplicationFactory, Application, ApplicationResult,
    CommandLineError,
)
from logutil import LogTestCase
import mockapp.log as ml
import mockapp.app as ma


class TestActionSecondPass(LogTestCase):
    def setUp(self):
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
        self.assertEqual('u', opt.short_name)
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
        self.assertEqual(5, len(meta.options))
        self.assertEqual(False, meta.first_pass)

        opt: OptionMetaData = meta.options_by_name['arg2']
        self.assertEqual('arg2', opt.long_name)
        self.assertEqual('2', opt.short_name)
        self.assertEqual('str1x', opt.default)
        self.assertEqual('STRING', opt.metavar)
        self.assertEqual(str, opt.dtype)

        opt: OptionMetaData = meta.options_by_name['fruit']
        self.assertEqual('f', opt.short_name)
        self.assertEqual('a tasty selection', opt.doc)
        self.assertEqual('<apple|banana>', opt.metavar)
        self.assertEqual(('apple', 'banana'), opt.choices)
        self.assertEqual('fruit', opt.dest)
        self.assertEqual(ma.Fruit.banana, opt.default)
        self.assertEqual(ma.Fruit, opt.dtype)

        pos = meta.positional
        self.assertEqual(3, len(pos))
        self.assertEqual('a1', pos[0].name)
        self.assertEqual(str, pos[0].dtype)
        self.assertEqual('arg0', pos[1].name)
        self.assertEqual(float, pos[1].dtype)
        self.assertEqual('z', pos[2].name)
        self.assertEqual(ma.Fruit, pos[2].dtype)


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
        self.assertEqual('u', opt.short_name)
        self.assertEqual('the level to set the root logger', opt.doc)

        TestActionSecondPass._test_second_action(self, actions)


class TestActionInvoke(LogTestCase):
    def setUp(self):
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-first-pass.conf')

    def test_first_pass_invoke(self):
        aset: CommandActionSet = self.cli.create('one 2 apple -g 5 -e debug'.split())
        if 0:
            print()
            self.cli.parser.write_help()
            self.config_logging('zensols.cli')
        insts = aset.invoke()
        self.assertEqual(2, len(insts))
        res: Application = insts[0]
        self.assertEqual(ApplicationResult, type(res))
        self.assertTrue(isinstance(res.instance, ml.LogConfigurator))
        self.assertEqual((None, ml.LogLevel.debug, ml.LogLevel.warning),
                         res.result)
        self._test_second_action(insts[1])

    def _test_second_action(self, res: Application):
        self.assertTrue(isinstance(res.instance, ma.TestAction))
        res_params = ('one', 2.0, 5, 'str1x', ma.Fruit.banana, ma.Fruit.apple)
        self.assertEqual(res_params, res.instance.invoke_state)
        self.assertEqual(('one', 2.0, 5, 'str1x', ma.Fruit.banana, ma.Fruit.apple, 'r'), res.result)
        self.assertEqual((str, float, int, str, ma.Fruit, ma.Fruit), tuple(map(type, res_params)))

    def test_second_pass_invoke(self):
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-sec-pass.conf')
        aset: CommandActionSet = self.cli.create('doit one 2 apple -g 5'.split())
        if 0:
            print()
            self.cli.parser.write_help()
            self.config_logging('zensols.cli')
        insts = aset.invoke()
        self.assertEqual(1, len(insts))
        self._test_second_action(insts[0])


class TestActionType(LogTestCase):
    def setUp(self):
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-bool.conf')

    def test_bool(self):
        aset: CommandActionSet = self.cli.create('actionone'.split())
        if 0:
            print()
            self.cli.parser.write_help()
            self.config_logging('zensols.cli')
        insts = aset.invoke()
        self.assertEqual(1, len(insts))
        res: Application = insts[0]
        self.assertTrue(isinstance(res.instance, ma.TestActionBool))
        self.assertEqual(('action1', False), res.result)

        aset: CommandActionSet = self.cli.create('actionone -o'.split())
        insts = aset.invoke()
        res: Application = insts[0]
        self.assertEqual(('action1', True), res.result)

        msg: str = r"^action 'action2' expects 1.*"
        with self.assertRaisesRegex(CommandLineError, msg):
            aset: CommandActionSet = self.cli.create('action2'.split())

        aset: CommandActionSet = self.cli.create('action2 nada'.split())
        insts = aset.invoke()
        res: Application = insts[0]
        self.assertEqual(('action2', True), res.result)

    def test_wrong_type(self):
        aset: CommandActionSet = self.cli.create('action3'.split())
        if 0:
            print()
            self.cli.parser.write_help()
            self.config_logging('zensols.cli')
        insts = aset.invoke()
        self.assertEqual(1, len(insts))
        res: Application = insts[0]
        self.assertTrue(isinstance(res.instance, ma.TestActionBool))
        self.assertEqual(('action3', None), res.result)

        aset: CommandActionSet = self.cli.create('action3 -t 3'.split())
        insts = aset.invoke()
        res: Application = insts[0]
        self.assertTrue(isinstance(res.instance, ma.TestActionBool))
        self.assertEqual(('action3', 3), res.result)

        usage: str = ''
        with self.assertRaises(SystemExit):
            stdold = sys.stderr
            try:
                sys.stderr = StringIO()
                self.cli.create('action3 -t notint'.split())
            finally:
                usage = sys.stderr.getvalue()
                sys.stderr = stdold
        self.assertRegex(
            usage, r".*error: option -t: invalid integer value: 'notint'.*")


class TestActionMetaConfig(LogTestCase):
    def test_first_pass_invoke(self):
        self.cli = ApplicationFactory.instance(
            'zensols.testapp', 'test-resources/test-app-meta.conf')
        aset: CommandActionSet = self.cli.create('action3 -o'.split())
        if 0:
            print()
            self.cli.parser.write_help()
            self.config_logging('zensols.cli')
        insts = aset.invoke()
        res: Application = insts[0]
        self.assertEqual(('bad meth name', True), res.result)

        aset: CommandActionSet = self.cli.create('act4 nada'.split())
        insts = aset.invoke()
        res: Application = insts[0]
        self.assertEqual(('action2', 'nada'), res.result)
