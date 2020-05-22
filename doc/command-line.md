# Command Line Interface

If you want to skip templating it out (i.e. don't like Java), create a command
line module:

```python
from zensols.cli import OneConfPerActionOptionsCli
from zensols.cli import SimpleActionCli
from zensols.tools import HelloWorld

VERSION='0.1'

class ConfAppCommandLine(OneConfPerActionOptionsCli):
    def __init__(self):
        cnf = {'executors':
               [{'name': 'hello',
                 'executor': lambda params: HelloWorld(**params),
                 'actions':[{'name': 'doit',
                             'meth': 'print_message',
                             'opts': [['-m', '--message', True, # require argument
                                       {'dest': 'message', 'metavar': 'STRING',
                                        'help': 'a message to print'}]]}]}],
               # uncomment to add a configparse (ini format) configuration file
               # 'config_option': {'name': 'config',
               #                   'opt': ['-c', '--config', False,
               #                           {'dest': 'config', 'metavar': 'FILE',
               #                            'help': 'configuration file'}]},
               'whine': 1}
        super(ConfAppCommandLine, self).__init__(cnf, version=VERSION)

def main():
    cl = ConfAppCommandLine()
    cl.invoke()
```

This uses the `OneConfPerActionOptionsCliEnv` class, which provides a data
driven way of configuring the action based command line.  An extention of this
class is the `OneConfPerActionOptionsCliEnv` class, which imports environment
variables and allows adding to the configuration via adding a resource like
file (i.e. `~/.<program name>rc`) type file.  See the
