import logging
import unittest
from zensols.config import IniConfig
from zensols.cli import (
    PerActionOptionsCli,
    OneConfPerActionOptionsCli,
)

logger = logging.getLogger(__name__)


class AppTester(object):
    def __init__(self, some_opt_name, a_file_name, config=None,
                 a_num_option=None, amand_opt=None):
        self.some_opt_name = some_opt_name
        self.a_file_name = a_file_name
        self.a_num_option = a_num_option

    def startaction(self):
        logger.debug('start action')
        current_test.assertEqual(test_opt_gval, self.some_opt_name)
        current_test.assertEqual(test_file_gval, self.a_file_name)
        current_test.assertEqual(test_args_gval, self.args)

    def stopaction(self):
        logger.debug('stop action')
        current_test.assertEqual(test_opt_gval, self.some_opt_name + '_stop')
        current_test.assertEqual(test_file_gval, self.a_file_name + '_stop')
        current_test.assertEqual(test_args_gval, self.args)
        current_test.assertEqual(test_num_gval, self.a_num_option)

    def set_args(self, args):
        self.args = args


class AppCommandLine(PerActionOptionsCli):
    def __init__(self, conf_file=None, use_environ=False, config_mand=False):
        opts = {'some_opt_name', 'config', 'a_file_name', 'a_num_option'}
        manditory_opts = {'some_opt_name'}
        if config_mand:
            manditory_opts.update({'config'})
        if use_environ:
            environ_opts = opts
        else:
            environ_opts = {}
        executors = {'app_test_key': lambda params: AppTester(**params)}
        invokes = {'start': ['app_test_key', 'startaction', 'test doc'],
                   'stop': ['app_test_key', 'stopaction', 'test doc']}
        if conf_file:
            conf = IniConfig(conf_file, robust=True)
        else:
            conf = None
        super(AppCommandLine, self).__init__(
            executors, invokes, config=conf,
            opts=opts, manditory_opts=manditory_opts,
            environ_opts=environ_opts)

    def _config_logging(self, level):
        pass

    def _parser_error(self, msg):
        raise ValueError(msg)

    def config_parser(self):
        parser = self.parser
        self._add_whine_option(parser)
        parser.add_option('-o', '--optname', dest='some_opt_name')
        self.action_options['start'] = [{'opt_obj': self.make_option('-f', '--file', dest='a_file_name'),
                                         'manditory': False}]
        self.action_options['stop'] = [{'opt_obj': self.make_option('-x', '--xfile', dest='a_file_name'),
                                        'manditory': False},
                                       {'opt_obj': self.make_option('-n', '--num', dest='a_num_option', type='int'),
                                        'manditory': False}]


class TestCommandOpTest(unittest.TestCase):
    def setUp(self):
        global current_test
        current_test = self

    def conf(self, mand_on=False):
        cnf = {'executors':
               [{'name': 'app_testor',
                 'executor': lambda params: AppTester(**params),
                 'actions': [{'name': 'start',
                              'meth': 'startaction',
                              'doc': 'start doc',
                              'opts': [['-f', '--file', False, {'dest': 'a_file_name'}]]},
                             {'name': 'stop',
                              'meth': 'stopaction',
                              'doc': 'stop doc',
                              'opts': [['-x', '--xfile', False, {'dest': 'a_file_name'}],
                                       ['-n', '--num', False, {'dest': 'a_num_option', 'type': 'int'}],
                                       [None, '--amand_opt', mand_on, {}]]}]}],
               'global_options': [['-o', '--optname', False, {'dest': 'some_opt_name'}]],
               'whine': True}
        return cnf

    def test_per_action_options(self):
        logger.debug('test_per_action_options')
        global test_opt_gval, test_file_gval, test_args_gval, test_num_gval
        test_opt_gval = 'test1'
        test_file_gval = 'afile'
        test_args_gval = ['another_arg']
        AppCommandLine().invoke('start -o test1 -f afile another_arg'.split(' '))
        test_opt_gval = 'test1_stop'
        test_file_gval = 'afile_stop'
        test_num_gval = 123454321
        AppCommandLine().invoke('stop -n 123454321 -o test1 -x afile another_arg'.split(' '))

    def test_per_action_one_conf(self):
        global test_opt_gval, test_file_gval, test_args_gval, test_num_gval
        logger.debug('test_per_action_one_conf')
        test_opt_gval = 'test1'
        test_file_gval = 'afile'
        test_args_gval = ['another_arg']
        cnf = self.conf(False)
        #OneConfPerActionOptionsCli(cnf).invoke(['-h'])
        OneConfPerActionOptionsCli(cnf).invoke('start -o test1 -f afile another_arg'.split(' '))
        test_opt_gval = 'test1_stop'
        test_file_gval = 'afile_stop'
        test_num_gval = 123454321
        cnf = self.conf()
        OneConfPerActionOptionsCli(cnf).invoke('stop -o test1 -x afile another_arg -n 123454321'.split(' '))

    def test_missing_mandated_opt(self):
        logger.debug('test_missing_mandated_opt')

        class TestMissingOptCli(OneConfPerActionOptionsCli):
            def _config_logging(self, level):
                pass

            def _parser_error(self, msg):
                raise ValueError(msg)

        def run_missing_opt():
            global test_opt_gval, test_file_gval, test_args_gval, test_num_gval
            test_opt_gval = 'test1_stop'
            test_file_gval = 'afile_stop'
            test_args_gval = ['another_arg']
            test_num_gval = 123454321
            cnf = self.conf(True)
            TestMissingOptCli(cnf).invoke('stop -o test1 -x afile another_arg -n 123454321'.split(' '))

        self.assertRaises(ValueError, run_missing_opt)
