import logging
import unittest
import os
from zensols.config import ExtendedInterpolationConfig
from zensols.cli import OneConfPerActionOptionsCliEnv

logger = logging.getLogger(__name__)


class AppTester(object):
    def __init__(self, some_opt_name, config=None):
        current_test.assertEqual(good_conf, type(config))
        self.some_opt_name = some_opt_name

    def startaction(self):
        current_test.assertEqual(good_val, self.some_opt_name)


class ConfAppCommandLine(OneConfPerActionOptionsCliEnv):
    def __init__(self, conf_var=None, expect=False):
        str_opt = ['-s', '--someopt', False,
                   {'dest': 'some_opt_name',
                    'metavar': 'STRING',
                    'help': 'help message'}]
        cnf = {'executors':
               [{'name': 'distribution',
                 'executor': lambda params: AppTester(**params),
                 'actions': [{'name': 'start',
                              'meth': 'startaction',
                              'doc': 'pretty print discovery information',
                              'opts': [str_opt]}]}],
               'config_option': {'name': 'config',
                                 'expect': expect,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config', 'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(
            cnf, config_env_name=conf_var,
            config_type=ExtendedInterpolationConfig)


class TestActionCliEnvironment(unittest.TestCase):
    def setUp(self):
        global current_test, good_val
        current_test = self

    def test_env_conf(self):
        global good_val, good_conf
        good_val = 'conf-test1'
        good_conf = ExtendedInterpolationConfig
        ConfAppCommandLine().invoke('start -c test-resources/actioncli-test.conf'.split())

    def test_env_conf_cli_override(self):
        global good_val, good_conf
        good_val = 'testenvconf'
        good_conf = ExtendedInterpolationConfig
        ConfAppCommandLine().invoke('start -c test-resources/actioncli-test.conf  --someopt testenvconf'.split())

    def test_env_conf_cli_interpolate(self):
        global good_val, good_conf
        good_val = 'p1.conf-test1'
        good_conf = ExtendedInterpolationConfig
        ConfAppCommandLine().invoke('start -c test-resources/actioncli-test3.conf'.split())

    def test_env_conf_cli_env(self):
        global good_val, good_conf
        good_val = 'p1.conf-test1'
        good_conf = ExtendedInterpolationConfig
        os.environ['SOMERC'] = 'test-resources/actioncli-test3.conf'
        try:
            ConfAppCommandLine('somerc', True).invoke('start'.split())
        finally:
            del os.environ['SOMERC']

    def test_env_conf_cli_env_missing(self):
        global good_val, good_conf
        good_val = None
        good_conf = type(None)
        ConfAppCommandLine('somerc', False).invoke('start'.split())

    def test_env_conf_cli_env_missing_raise(self):
        global good_val, good_conf
        good_val = 'p1.conf-test1'
        good_conf = ExtendedInterpolationConfig
        os.environ['SOMERC'] = 'NOFILE'

        def run_missing_env():
            try:
                ConfAppCommandLine('somerc', True).invoke('start'.split())
            finally:
                del os.environ['SOMERC']
        self.assertRaises(OSError, run_missing_env)
