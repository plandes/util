# Zensols Utilities

[![Travis CI Build Status][travis-badge]][travis-link]
[![PyPI][pypi-badge]][pypi-link]
[![Python 3.7][python37-badge]][python37-link]

Command line, configuration and persistence utilities generally used for any
more than basic application.  This general purpose library is small, has few
dependencies, and helpful across many applications.  Some features include:

* Better application level support for [configuration] than [configparser].
  Specifically, optional configuration and configuration groups.
* Construct objects using configuration files (both INI and YAML).
* A [command action library] using an action mnemonic to invocation of a
  handler that is integrated with a the configuration API.  This supports long
  and short GNU style options as provided by [optparse].
* Streamline in memory and on disk persistence.
* Multi-processing work with a persistence layer.


## Obtaining

The easiest way to install the command line program is via the `pip` installer:
```bash
pip3 install zensols.util
```

## Documentation

Framework documentation [API Reference](https://plandes.github.io/util/)


## Template

The easiest to get started is to [template] out this project is to create your
own boilerplate project with the `mkproj` utility.  This requires a [Java
installation], and easy to create a Python boilerplate with the following
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

This creates a project customized with your organization's name, author, and
other details about the project.  In addition, it also creates a sample
configuration file and command line that is ready to be invoked by either a
Python REPL or from the command line via [GNU make].

If you don't want to bother installing this program, the following sections
have generated code as examples from which you can copy/paste.


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

[MIT License](LICENSE.md)

Copyright (c) 2020 Paul Landes


<!-- links -->
[travis-link]: https://travis-ci.org/plandes/util
[travis-badge]: https://travis-ci.org/plandes/util.svg?branch=master
[pypi]: https://pypi.org/project/zensols.util/
[pypi-link]: https://pypi.python.org/pypi/zensols.util
[pypi-badge]: https://img.shields.io/pypi/v/zensols.util.svg
[python37-badge]: https://img.shields.io/badge/python-3.7-blue.svg
[python37-link]: https://www.python.org/downloads/release/python-370

[template]: https://github.com/plandes/template
[GNU make]: https://www.gnu.org/software/make/
[configparser]: https://docs.python.org/3/library/configparser.html
[Java installation]: https://java.com/en/download/
[optparse]: https://docs.python.org/3/library/optparse.html

[command action library]: doc/command-line.md
[configuration]: doc/config.md
