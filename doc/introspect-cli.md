# Introspective Command Line Interface

The goal of this API is to require little to no meta data to create a command
line.  Instead, a complete command line interface is automatically built given
a class and follows from the structure and meta data of the class itself.

This API replaces the [SimpleActionCli] and its sub classes, which will
eventually be removed from a future major release.

Like the other documentation, this covers the command line API as a tutorial
and points out the API for further perusing in a breadth first manner.  As this
API is build on the [configuration], please read or skim that documentation
first.  We'll start with a simple application and build it up, with the final
version being the CLI [example] directory.


## Boilerplate

Every introspective CLI application needs an *application context*, which is
just a specialized grouping of data specific to an application that has two
forms: file(s) on the file system and their in-memory isomorphic form.  The
files that make up the application context are those already detailed in the
[configuration] section.  The *application context* file always has the same
name and directory structure (`resources/app.conf`), which is added as a
resource file to a package distribution built with [setuptools]:
```ini
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: app

[app]
class_name = payroll.Tracker
```

The class [ActionCliManager] is used by the framework to build the command line
and link it to the target class(es), and is configured in the `cli` section.
The `app` section defines a the instance that will be the target of the
framework, and will invoke a method on the class when run from the command
line from `__main__`.  The `apps` line in the `cli` section lists all the
application to create, each of which maps as an *action* using a mnemonic for
each of it's methods.

Since this example creates a simple payroll application, we'll create a *hello
world* like class in `payroll.py` that will evolve in to a more complex
application:
```python
from dataclasses import dataclass


@dataclass
class Tracker(object):
    def print_employees(self):
        print('hello world')
```

Finally, we need the entry point main, which is added to `main.py`:
```python
#!/usr/bin/env python

from zensols.cli import ApplicationFactory


def main():
    cli = ApplicationFactory('mycom.payroll')
    cli.invoke()


if __name__ == '__main__':
    main()
```

The [ApplicationFactory] is the framework entry point that requires only one
parameter, which is the package distribution name and usually the name space of
the application.  When we run this application from the command line using a
help flag (`--help`), we get:
```bash
$ ./main.py --help

Usage: main.py [options]:

Tracker().

Options:
  --version   show program's version number and exit
  -h, --help  show this help message and exit
```

The help usage message is built automatically, so the flag is always present in
the usage.  The `Tracker()` is automatically generated program level
documentation since we have not given any docstrings in our class.

The version, when built and installed as an entry point command line file, will
print the version.  Since there is only one method, and thus one action mapped
to that method, the CLI calls it and produces the expected output.
```bash
$ ./main.py --help
hello world
```

## Domain

Let's add some container classes in `domain.py` to hold data for our payroll
system, which are employees and their salaries and a grouping for them by
department:
```python
from typing import Tuple
from dataclasses import dataclass, field
from zensols.config import Dictable


@dataclass
class Person(Dictable):
    name: str
    age: int
    salary: float


@dataclass
class Department(Dictable):
    name: str
    employees: Tuple[Person] = field(default_factory=lambda: ())

    def __str__(self):
        emp_names = ', '.join(map(lambda p: p.name, self.employees))
        return f"{self.name}: {emp_names}"
```


## Complete Examples

See the [example] directory the complete code used to create the examples in
this documentation.


<!-- links -->

[example]: https://github.com/plandes/util/tree/master/example/cli
[configuration]: config.md
[setuptools]: https://setuptools.readthedocs.io/en/latest/
