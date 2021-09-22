# Zensols Utilities

[![PyPI][pypi-badge]][pypi-link]
[![Python 3.7][python37-badge]][python37-link]
[![Python 3.8][python38-badge]][python38-link]
[![Python 3.9][python39-badge]][python39-link]
[![Build Status][build-badge]][build-link]

Command line, configuration and persistence utilities generally used for any
more than basic application.  This general purpose library is small, has few
dependencies, and helpful across many applications.

* See the [full documentation].
* Paper on [arXiv](http://arxiv.org/abs/2109.03383).

Some features include:

* A [Hydra] or [Java Spring] like application level support for [configuration]
  than [configparser].
  * Construct objects using configuration files (both INI and YAML).
  * Parse primitives, dictionaries, file system objects, instances of classes.
* A [command action library] using an action mnemonic to invocation of a
  handler that is integrated with a the configuration API.  This supports long
  and short GNU style options as provided by [optparse].
* Streamline in memory and on disk [persistence](doc/persist.md).
* Multi-processing work with a [persistence layer](doc/persist.md).

A secondary goal of the API is to make prototyping Python code quick and easy
using the REPL.  Examples include reloading modules in the [configuration
factory](doc/config.md).


## Documentation

* [Full documentation](https://plandes.github.io/util/)
* [Configuration](https://plandes.github.io/util/doc/config.html): powerful but
  simple configuration system much like [Hydra] or [Java Spring]
* [Command line](https://plandes.github.io/util/doc/command-line.html):
  automagically creates a fully functional command with help from a Python
  [dataclass](https://docs.python.org/3/library/dataclasses.html)
* [Persistence](https://plandes.github.io/util/doc/persist.html): cache
  intermediate data(structures) to the file system
* [API reference](https://plandes.github.io/install/api.html)


## Obtaining

The easiest way to install the command line program is via the `pip` installer:
```bash
pip3 install zensols.util
```


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


## Citation

If you use this project in your research please use the following BibTeX entry:
```
@article{Landes_DiEugenio_Caragea_2021,
  title={DeepZensols: Deep Natural Language Processing Framework},
  url={http://arxiv.org/abs/2109.03383},
  note={arXiv: 2109.03383},
  journal={arXiv:2109.03383 [cs]},
  author={Landes, Paul and Di Eugenio, Barbara and Caragea, Cornelia},
  year={2021},
  month={Sep}
}
```


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

[MIT License](LICENSE.md)

Copyright (c) 2020 - 2021 Paul Landes


<!-- links -->
[pypi]: https://pypi.org/project/zensols.util/
[pypi-link]: https://pypi.python.org/pypi/zensols.util
[pypi-badge]: https://img.shields.io/pypi/v/zensols.util.svg
[python37-badge]: https://img.shields.io/badge/python-3.7-blue.svg
[python37-link]: https://www.python.org/downloads/release/python-370
[python38-badge]: https://img.shields.io/badge/python-3.8-blue.svg
[python38-link]: https://www.python.org/downloads/release/python-380
[python39-badge]: https://img.shields.io/badge/python-3.9-blue.svg
[python39-link]: https://www.python.org/downloads/release/python-390
[build-badge]: https://github.com/plandes/util/workflows/CI/badge.svg
[build-link]: https://github.com/plandes/util/actions

[Java Spring]: https://spring.io
[Hydra]: https://github.com/facebookresearch/hydra
[Java installation]: https://java.com/en/download/

[full documentation]: https://plandes.github.io/util/
[template]: https://github.com/plandes/template
[GNU make]: https://www.gnu.org/software/make/
[configparser]: https://docs.python.org/3/library/configparser.html
[optparse]: https://docs.python.org/3/library/optparse.html

[command action library]: doc/command-line.md
[configuration]: doc/config.md
