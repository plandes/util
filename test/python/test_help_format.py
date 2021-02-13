import unittest
from io import StringIO
from zensols.cli import (
    OneConfPerActionOptionsCli,
    PrintActionsOptionParser,
)


class AppTester(object):
    def __init__(self):
        pass

    def info(self):
        pass

    def sync(self):
        pass

    def mount_all(self):
        pass

    def umount_all(self):
        pass


class ConfAppCommandLine(OneConfPerActionOptionsCli):
    def __init__(self):
        dry_run_op = ['-d', '--dryrun', False,
                      {'dest': 'dry_run',
                       'action': 'store_true', 'default': False,
                       'help': 'dry run to not actually connect, but act like it'}]
        sources_op = ['-n', '--sources', False,
                      {'dest': 'source_names',
                       'help': 'override the sources property in the config'}]
        sources_op = ['-n', '--sources', False,
                      {'dest': 'source_names',
                       'help': 'override the sources property in the config'}]
        datdir_op = ['-d', '--datadir', False,
                     {'dest': 'data_dir', 'metavar': 'FILE',
                      'default': '~/opt/datadir',
                      'help': 'the location of the Zotero data directory'}]
        outdir_op = ['-o', '--outputdir', True,
                     {'dest': 'out_dir', 'metavar': 'DIRECTORY',
                      'default': '.',
                      'help': 'the directory to output the website'}]
        cnf = {'executors':
               [{'name': 'backup',
                 'executor': lambda params: AppTester(**params),
                 'actions':[{'name': 'info',
                             'doc': 'print backup configuration information'},
                            {'name': 'backupreallylong',
                             'meth': 'sync',
                             'doc': 'run the backup',
                             'opts': [dry_run_op, sources_op]},
                            {'name': 'mount',
                             'meth': 'mount_all',
                             'doc': 'mount all targets',
                             'opts': [datdir_op]},
                            {'name': 'umount',
                             'meth': 'umount_all',
                             'doc': 'un-mount all targets',
                             'opts': [datdir_op, outdir_op]}]}],
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(cnf)

    def _create_parser(self, usage=''):
        class NoExitParser(PrintActionsOptionParser):
            def exit(self, status=0, msg=None):
                pass
        return NoExitParser(
            usage=usage, version='%prog ' + str(self.version))


class TestHelpFormatter(unittest.TestCase):
    HELP = """\
Usage: python -m unittest <list|backupreallylong|info|mount|umount> [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -w NUMBER, --whine=NUMBER
                        add verbosity to logging
Actions:
  backupreallylong  Run the backup
  -d, --dryrun                                dry run to not actually connect, but act like it
  -n, --sources <STRING>                      override the sources property in the config

  info              Print backup configuration information

  mount             Mount all targets
  -d, --datadir <FILE>         ~/opt/datadir  the location of the Zotero data directory

  umount            Un-mount all targets
  -d, --datadir <FILE>         ~/opt/datadir  the location of the Zotero data directory
  -o, --outputdir <DIRECTORY>  .              the directory to output the website
"""

    def setUp(self):
        self.maxDiff = 9999999

    def test_help_formatting(self):
        if True:
            cli = ConfAppCommandLine()
            parser = cli._create_parser()
            cli.parser = parser
            cli.config_parser()
            sio = StringIO()
            cli.parser.print_help(sio)
            self.assertEqual(self.HELP, sio.getvalue())
        else:
            ConfAppCommandLine().invoke([''])
