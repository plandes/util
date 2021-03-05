import unittest
import os
from zensols.cli import SimpleActionCli
from zensols.config import ConfigurableError, IniConfig


class AppTester(object):
    def __init__(self, some_opt_name, config=None):
        current_test.assertEqual(good_conf, type(config))
        self.some_opt_name = some_opt_name

    def startaction(self):
        current_test.assertEqual(good_val, self.some_opt_name)


class AppCommandLine(SimpleActionCli):
    def __init__(self, conf_file=None, use_environ=False, config_mand=False):
        opts = {'some_opt_name', 'config'}
        manditory_opts = {'some_opt_name'}
        if config_mand:
            manditory_opts.update({'config'})
        if use_environ:
            environ_opts = opts
        else:
            environ_opts = {}
        executors = {'app_test_key': lambda params: AppTester(**params)}
        invokes = {'info': ['app_test_key', 'startaction', 'test doc']}
        if conf_file:
            conf = IniConfig(conf_file)
        else:
            conf = None
        super(AppCommandLine, self).__init__(
            executors, invokes, config=conf, opts=opts,
            manditory_opts=manditory_opts, environ_opts=environ_opts)

    def _parser_error(self, msg):
        raise ValueError(msg)

    def config_parser(self):
        parser = self.parser
        self._add_whine_option(parser)
        parser.add_option('-o', '--optname', dest='some_opt_name')


class TestActionCli(unittest.TestCase):
    def setUp(self):
        global current_test, good_val
        current_test = self

    def test_default(self):
        global good_val, good_conf
        good_val = 'test1'
        good_conf = type(None)
        AppCommandLine().invoke('info -o test1'.split(' '))
        good_val = 'test2'
        AppCommandLine().invoke('info -o test2'.split(' '))

    def test_missing_mandated_opt(self):
        def run_missing_opt():
            global good_val
            good_val = None
            AppCommandLine().invoke('info'.split(' '))
        self.assertRaises(ValueError, run_missing_opt)

    def test_missing_non_mandated_opt(self):
        def run_missing_opt():
            global good_val
            good_val = 'test2'
            AppCommandLine(config_mand=True).invoke('info -o test2'.split(' '))
        self.assertRaises(ValueError, run_missing_opt)

    def test_with_config(self):
        global good_val, good_conf
        good_val = 'test1'
        good_conf = IniConfig
        with self.assertRaisesRegex(ConfigurableError, r'^no such file: test-resources.*'):
            AppCommandLine('test-resources/actioncli-test.confDNE').invoke(
                'info -o test1'.split(' '))
        good_val = 'conf-test1'
        AppCommandLine('test-resources/actioncli-test.conf').invoke(
            'info'.split(' '))
        good_val = 'conf-test2'
        AppCommandLine('test-resources/actioncli-test2.conf').invoke(
            'info'.split(' '))

    def test_with_override_config(self):
        global good_val, good_conf
        good_val = 'testx'
        good_conf = IniConfig
        AppCommandLine('test-resources/actioncli-test.conf').invoke(
            'info -o testx'.split(' '))

    def test_with_env_config(self):
        global good_val, good_conf
        good_val = 'test1'
        good_conf = type(None)
        os.environ['SOME_OPT_NAME'] = 'test1'
        AppCommandLine(use_environ=True).invoke('info'.split(' '))
        del os.environ['SOME_OPT_NAME']
