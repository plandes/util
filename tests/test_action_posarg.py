from typing import Tuple, Any
from logutil import LogTestCase
import mockapp.app as ma
from zensols.cli import (
    CommandLineError, CommandActionSet,
    ApplicationResult, ActionResult, ApplicationFactory
)


class TestActionSecondPass(LogTestCase):
    def setUp(self):
        self.cli = ApplicationFactory(
            'zensols.testapp', 'test-resources/test-app-posarg.conf')

    def _test_help(self):
        print()
        self.cli.parser.write_help()
        self.config_logging('zensols.cli')

    def _test(self, args: str, should: Any):
        aset: CommandActionSet = self.cli.create(args.split())
        app_res: ApplicationResult = aset.invoke()
        self.assertEqual(ApplicationResult, type(app_res))
        self.assertEqual(1, len(app_res))
        action_res: ActionResult = app_res[0]
        self.assertEqual(ActionResult, type(action_res))
        self.assertEqual(ma.TestPositionalArguments, type(action_res.instance))
        res: Any = action_res.result
        self.assertEqual(should, res)

    def _err(self, name: str, expect: int, got: int):
        return f"^Action '{name}' expects at least {expect} positional parameter\\(s\\) but got {got}$"

    def test_pos(self):
        self._test('noarg', {})

        self._test('onearg farg', {'first': 'farg'})
        with self.assertRaisesRegex(CommandLineError, self._err('onearg', 1, 0)):
            self._test('onearg', {})
        self._test('twoarg farg sarg', {'first': 'farg', 'second': 'sarg'})

        with self.assertRaisesRegex(CommandLineError, self._err('twoarg', 2, 0)):
            self._test('twoarg', {})

        with self.assertRaisesRegex(CommandLineError, self._err('twoarg', 2, 1)):
            self._test('twoarg sarg', {})

    def test_multi(self):
        self._test('multiargs', {'margs': ()})
        self._test('multiargs foo', {'margs': ('foo',)})
        self._test('multiargs foo bar', {'margs': ('foo', 'bar')})

    def test_pos_multi(self):
        self._test('multiargswfirst first', {'first': 'first', 'margs': ()})
        self._test('multiargswfirst first foo',
                   {'first': 'first', 'margs': ('foo',)})
        self._test('multiargswfirst first foo bar',
                   {'first': 'first', 'margs': ('foo', 'bar')})
        with self.assertRaisesRegex(CommandLineError,
                                    self._err('multiargswfirst', 1, 0)):
            self._test('multiargswfirst', {})

    def test_pos_multi_loc(self):
        def multarg(name: str, margcmd: str, margs: Tuple[str, ...]):
            self._test(f'{name} first sarg {margcmd}',
                       {'first': 'first',
                        'second': 'sarg',
                        'margs': margs})

        multarg('multiargswsecond', '', ())
        multarg('multiargswsecond', 'baz', ('baz',))
        multarg('multiargswsecond', 'foo bar', ('foo', 'bar'))
        with self.assertRaisesRegex(CommandLineError,
                                    self._err('multiargswsecond', 2, 0)):
            self._test('multiargswsecond', {})
        with self.assertRaisesRegex(CommandLineError,
                                    self._err('multiargswsecond', 2, 1)):
            self._test('multiargswsecond some', {})

        multarg('multiargsmargloc', '', ())
        multarg('multiargsmargloc', 'foo', ('foo',))
        multarg('multiargsmargloc', 'foo bar', ('foo', 'bar'))

        multarg('multiargsmargloc2', '', ())
        multarg('multiargsmargloc2', 'foo', ('foo',))
        multarg('multiargsmargloc2', 'foo bar', ('foo', 'bar'))

    def _test_multi_opt(self, name: str):
        should = {
            'val': 'defaultval',
            'vdef': 'defaultdef',
            'first': 'farg',
            'second': 'sarg',
            'args': ()}

        self._test(f'{name} farg sarg', should)
        self._test(f'{name} farg sarg --val aval', should | {'val': 'aval'})
        self._test(f'{name} --val aval farg sarg', should | {'val': 'aval'})
        self._test(f'{name} farg --val aval sarg', should | {'val': 'aval'})
        self._test(f'{name} farg --val aval --vdef adef sarg',
                   should | {'val': 'aval', 'vdef': 'adef'})
        self._test(f'{name} --vdef adef farg --val aval sarg',
                   should | {'val': 'aval', 'vdef': 'adef'})

        self._test(f'{name} farg sarg one', should | {'args': ('one',)})
        self._test(f'{name} farg sarg one --val aval',
                   should | {'args': ('one',), 'val': 'aval'})
        self._test(f'{name} farg --val aval sarg one',
                   should | {'args': ('one',), 'val': 'aval'})
        self._test(f'{name} --val aval farg sarg one',
                   should | {'args': ('one',), 'val': 'aval'})

        self._test(f'{name} farg sarg one two', should | {'args': ('one', 'two')})
        self._test(f'{name} farg sarg one --val aval two',
                   should | {'args': ('one', 'two'), 'val': 'aval'})
        self._test(f'{name} farg --val aval sarg one two',
                   should | {'args': ('one', 'two'), 'val': 'aval'})
        self._test(f'{name} --val aval farg sarg one two',
                   should | {'args': ('one', 'two'), 'val': 'aval'})

    def test_multi_opt(self):
        self._test_multi_opt('mutiwdef')
        self._test_multi_opt('mutiwdef2')
