# Command Line Interface

The command line interface library intends to make command line execution and
configuration easy.  The library supports (among other features) an
mnemonic-centric way to tie a command line an *action* to a Python 3 handler
code segment.

The API provides an advanced command line interface library for quickly easily
tying action based commands, such as operands given after the program name, to
Python classes.

In this example, the `Cli` class is instantiated with `print_message` method
called with the `doit` command line action (given as the first parameter on the
command line).

This uses the [OneConfPerActionOptionsCli] class, which provides a data driven
way of configuring the action based command line.  An extention of this class
is the [OneConfPerActionOptionsCliEnv] class, which imports environment
variables and allows adding to the configuration via adding a resource like
file (i.e. `~/.<program name>rc`) type file.  See the
[configuration](config.md) documentation for more information.

Note that access to your program through this API is easily callable by other
programs by populating the `sys.argv` array and calling `main`.

```python
from zensols.cli import OneConfPerActionOptionsCliEnv
from dataclasses import dataclass, field, InitVar
from pathlib import Path
from zensols.config import ImportConfigFactory
from zensols.someproj import MainApplication, AppConfig


@dataclass
class Cli(object):
    config: AppConfig
    out_dir: InitVar[Path] = field(default=None)
    dry_run: InitVar[bool] = field(default=False)

    def __post_init__(self, out_dir: Path, dry_run: bool):
        self.factory = ImportConfigFactory(self.config)
        self.app: MainApplication = self.factory(
            'app', out_dir=out_dir, dry_run=dry_run)

    def print_message(self):
        self.app.tmp()


class ConfAppCommandLine(OneConfPerActionOptionsCliEnv):
    def __init__(self):
        dry_run_op = [None, '--dryrun', False,
                      {'dest': 'dry_run',
                       'action': 'store_true', 'default': False,
                       'help': 'do not do anything, just act like it'}]
        outdir_op = ['-o', '--outputdir', False, # does not require argument
                     {'dest': 'out_dir', 'metavar': 'DIRECTORY',
                      'help': 'the directory to output the website'}]
        cnf = {'executors':
               [{'name': 'exporter',
                 'executor': lambda params: Cli(**params),
                 'actions': [{'name': 'doit',
                              'meth': 'print_message',
                              'doc': 'action help explains how to do it',
                              'opts': [dry_run_op, outdir_op]}]}],
               'config_option': {'name': 'config',
                                 'expect': True,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config',
                                          'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 1}
        super().__init__(cnf, config_env_name='someprojrc',
                         pkg_dist='zensols.someproj',
                         config_type=AppConfig, no_os_environ=True)


def main():
    cl = ConfAppCommandLine()
    cl.invoke()
```

See the command line test case [test_cli_env.py] for more examples.


<!-- links -->

[template]: https://github.com/plandes/template

[OneConfPerActionOptionsCli]: ../api/zensols.cli.html#zensols.cli.peraction.OneConfPerActionOptionsCli
[OneConfPerActionOptionsCliEnv]: ../api/zensols.cli.html#zensols.cli.peraction.OneConfPerActionOptionsCliEnv
[test_cli_env.py]: https://github.com/plandes/util/tree/master/test/python/test_cli_env.py
