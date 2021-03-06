# Introspective Command Line

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

Every introspective CLI application needs an *application context* (see the
[configuration documentation](config.html#application-context)), which is
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
framework, and will invoke a method on the class when run from the command line
from `__main__`.  The `apps` line in the `cli` section lists all the
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

To access our container classes, we'll create a data access object and add it
to the `payroll.py` file:
```python
@dataclass
class EmployeeDatabase(object):
    departments: Tuple[Department]
```

We'll create a mock set of data directly in the `resources/app.conf` file to go
along with our mock DB instance and add the DB instance to the main app:
```ini
[homer]
class_name = domain.Person
age = 40
salary = 5.25

[human_resources]
class_name = domain.Department
name = hr
employees = instance: list: homer

[emp_db]
class_name = payroll.EmployeeDatabase
departments = instance: list: human_resources

[app]
class_name = payroll.Tracker
db = instance: emp_db
```


### Application Class and Actions

We'll flesh out our main application class with documentation and data class
field `dry_run`.
```python
@dataclass
class Tracker(object):
    """Tracks and distributes employee payroll."""
    db: EmployeeDatabase = field()
    """An instance not given on the commnd line."""

    dry_run: bool = field(default=False)
    """If given, don't do anything, just act like it."""

    def print_employees(self, format: Format = Format.short):
        """Show all employees."""
        logger.info(f'printing employees using format: {format}')
```

which gives the following help:
```bash
Usage: main.py [options]:

Show all employees.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -r, --dryrun          if given, don't do anything, just act like it
  -d EMPLOYEEDATABASE, --db=EMPLOYEEDATABASE
                        an instance not given on the commnd line
```

The `print_employees` method is now identified as the method to run on a new
instance of the class that will later be instantiated by the
[ImportConfigFactory] class by the framework.  The name for the framework
plumbing that ties the command line to this method is called an *action*.  Each
action has it's own respective arguments used as fields at the class level, and
optionally, any arguments given to the method (keyword or positional).


### Action Decorators

Now we have the try run boolean flag generated from our data class field
attribute and we see the method docstring used as the program documentation.
However, the `-d EMPLOYEEDATABASE` is the framework misinterpretation of the
reference to the data base object, which it should instead ignore.  There are
two ways to tell it to ignore it: a class space or a decorator class given in
the configuration.

The former is defined by creating the class space attribute `CLASS_META` that
contains what to make options, option name changes and mnemonic to method
mappings (see [LogConfigurator.CONFIG_META] for an example).

The latter is done by creating a new instance of a class in a section with the
same information as the `CONFIG_META` attribute.  The section name uses the
same section it *decorates* appended with `_decorates` in `resources/app.conf`,
such as:
```ini
[app_decorator]
class_name = zensols.cli.ActionCli
option_excludes = set: db
```
which tells the framework to ignore the `db` field.  The `ActionCli` is the
framework's aforementioned plumbing that connects the class and method pair to
the command line.  Each `ActionCli` describes the class and at least one of
it's methods, each of which is an action with it's respective command line
metadata given as an [ActionMetaData].


### Domain and Choices

We'll want to be able to allow different formats to print employees for our
`print_employees` method  However, this parameter will only apply to this
method and not every method of the class (unlike the `dryrun` field), so it's
given to our Python method as an optional keyword argument.

How we tell the program how to format is implemented as one of a set of
predefined constants, which is usually given as a *choice* in [OptionParser]
parlance.  The framework understands how to deal with choices as a Python
[Enum] class, so we'll add an enumeration for each format type with the
corresponding keyword argument to the method:
```python
from enum import Enum, auto

class Format(Enum):
    short = auto()
    verbose = auto()

def print_employees(self, format: Format = Format.short):
	"""Show all employees.

	:param format: the detail of reporting

	"""
	logger.info(f'printing employees using format: {format}')
	dept: Department
	for dept in self.db.departments:
		if format == Format.short:
			print(dept)
		else:
			dept.write()
```

Our generated help reflects the option as a keyword parameter and its default
to the method:
```bash
Usage: main.py [options]:

Show all employees.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d, --dryrun          if given, don't do anything, just act like it
  -f <short|verbose>, --format=<short|verbose>
                        the detail of reporting
```

Finally, we run the program with no options to invoke the `print_employees`
method:
```bash
$ ./main.py 
printing employees using format: Format.short
human_resources: homer

$ ./main.py -f verbose
printing employees using format: Format.verbose
name: human_resources
employees:
    name: homer
    age: 40
    salary: 5.25
```

## User Configuration

So far all the configuration we've seen is tied closely to the code, and not
the kind of configuration the end user cares about or should want to see.  This
framework allows a separation by inclusion of configuration with other files.
Typically the user indicates what file with a flag on the command line, which
the program then reads.

These files can reference each other, and for most use cases and this example,
refer from the application context to the user given data.  This user data will
have things like paths, user names, parameters to scientific applications etc.
The framework supports this and non-cyclical two way references: from the
application context to the user configuration and vice versa.

The framework implements this with the [ConfigurationImporter] class, which is
just a data class with a method to load the configuration and add it to the
application context.  It is configured as a *first pass* class, which means it
is run before the application.

### Two Pass Command Line Parser

The framework parses the command line parameters given by the user in two
passes:

1. The first pass parses options common to all applications and pertinent
   to tasks that usually prepare the environment before the application runs.
   Examples are configuring the log system with a debugging level, and in this
   example, loads the configuration.
   
   In this phase, all options from all methods are added so we can "fish out"
   the action mnemonic, which is the string used to indicate which method to
   run as we've seen with the `print_employees` method in the [application
   class](#application-class) example
   
2. After the first pass completes, we now know the action to run along with any
   other positional arguments given.



## Complete Examples

See the [example] directory the complete code used to create the examples in
this documentation.


<!-- links -->

[example]: https://github.com/plandes/util/tree/master/example/cli
[configuration]: config.md
[setuptools]: https://setuptools.readthedocs.io/en/latest/
