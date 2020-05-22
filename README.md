# Zensols Utilities

[![Travis CI Build Status][travis-badge]][travis-link]
[![PyPI][pypi-badge]][pypi-link]
[![Python 3.7][python37-badge]][python37-link]

Command line, configuration and persistence utilities generally used for any
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

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
## Table of Contents

- [Obtaining](#obtaining)
- [API](#api)
- [Usage](#usage)
    - [Command Line Interface](#command-line-interface)
- [Changelog](#changelog)
- [License](#license)

<!-- markdown-toc end -->



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

The API provides an advanced command line interface library for quickly easily
tying action based commands, such as operands given after the program name, to
Python classes.

See [Command Action Library](md/command-line.md).

See the [command line test cases](test/python/test_cli_env.py) for more
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
