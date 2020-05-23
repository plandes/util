# Command Line Interface

If you want to skip templating it out (i.e. don't like Java), create a command
line module:

```python
from zensols.cli import OneConfPerActionOptionsCliEnv
from zensols.someproj import (
    MainApplication,
    AppConfig,
)


class ConfAppCommandLine(OneConfPerActionOptionsCliEnv):
    def __init__(self):
        dry_run_op = [None, '--dryrun', False,
                      {'dest': 'dry_run',
                       'action': 'store_true', 'default': False,
                       'help': 'do not do anything, just act like it'}]
        msg_op = ['-m', '--message', True,  # require argument
                  {'dest': 'message', 'metavar': 'STRING',
                   'help': 'a message to print'}]
        outdir_op = ['-o', '--outputdir', False,
                     {'dest': 'out_dir', 'metavar': 'DIRECTORY',
                      'help': 'the directory to output the website'}]
        cnf = {'executors':
               [{'name': 'exporter',
                 'executor': lambda params: MainApplication(**params),
                 'actions': [{'name': 'doit',
                              'meth': 'print_message',
                              'doc': 'action help explains how to do it',
                              'opts': [dry_run_op, msg_op, outdir_op]}]}],
               'config_option': {'name': 'config',
                                 'expect': True,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config',
                                          'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(
            cnf, config_env_name='someprojrc', pkg_dist='zensols.someproj',
            config_type=AppConfig)


def main():
    cl = ConfAppCommandLine()
    cl.invoke()
```

This uses the `OneConfPerActionOptionsCliEnv` class, which provides a data
driven way of configuring the action based command line.  An extention of this
class is the `OneConfPerActionOptionsCliEnv` class, which imports environment
variables and allows adding to the configuration via adding a resource like
file (i.e. `~/.<program name>rc`) type file.

