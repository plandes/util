# Command line, configuration and persistence utilites.

[![Travis CI Build Status][travis-badge]][travis-link]
[![PyPI][pypi-badge]][pypi-link]
[![Python 3.7][python37-badge]][python37-link]

Command line, configuration and persistence utilites generally used for any
more than basic application.

The command line interface library intends to make command line execution and
configuration easy.  The library supports (among other features) an mnemonic
centric way to tie a command line an *action* to a Python 3 handler code
segment.  Features include:

* Better command line parsing than [optparse].  This a binding to from a
  command line option using an action mnemonic to invocation of a handler.
* Better application level support for configuration than [configparser].
  Specifically, optional configuration and configuration groups.

This package also has other packages to:

- Streamline in memory and on disk persistence
- Construct objects using configuration files (both INI and YAML).
- Multi-processing work with a persistence layer.


## Obtaining

The easiest way to install the command line program is via the `pip` installer:
```bash
pip3 install zensols.util
```


## Usage

The easiest to get started is to template out this project with the following
commands:

```bash
# clone the boilerplate repo
git clone https://github.com/plandes/template
# download the boilerplate tool
wget https://github.com/plandes/clj-mkproj/releases/download/v0.0.7/mkproj.jar
# create a python template and build it out
java -jar mkproj.jar config -s template/python
java -jar mkproj.jar
```


### Command Line Interface

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

See the [command line test cases](test/python/cli_env_test.py) for more
examples.


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

Copyright (c) 2020 Paul Landes

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


<!-- links -->
[travis-link]: https://travis-ci.org/plandes/util
[travis-badge]: https://travis-ci.org/plandes/util.svg?branch=master
[pypi]: https://pypi.org/project/zensols.util/
[pypi-link]: https://pypi.python.org/pypi/zensols.util
[pypi-badge]: https://img.shields.io/pypi/v/zensols.util.svg
[python37-badge]: https://img.shields.io/badge/python-3.7-blue.svg
[python37-link]: https://www.python.org/downloads/release/python-370
