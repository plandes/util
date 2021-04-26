# Command Line Interface

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

The remainder of the tutorial shows by example of how to use the framework.
The working example code at the end of each sub section can be found in the
[example] directory `example/cli`.  A more complete full example is given as a
template as described in the main documentation [template
section](../#template).


## Boilerplate

Every introspective CLI application needs an *application context* (see the
[configuration documentation](config.html#application-context)), which is just
a specialized grouping of data specific to an application that has two forms:
file(s) on the file system and their in-memory isomorphic form.  The files that
make up the application context are those already detailed in the
[configuration] section.  The *application context* file, which by default, is
`resources/app.conf`, which is added as a resource file to a package
distribution built with [setuptools] since the file is located in `resources`.
Our initial application context just provides the `cli` section with it's
referenced `app`:
```ini
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: app

[app]
class_name = payroll.Tracker
```

The class [ActionCliManager] is the framework class that builds the command
line and links it to the target class(es).  The `app` section gives the class
to instantiate, which has the method to call from the command line `__main__`.
The `apps` line in the `cli` section lists all the application to create, each
of which maps as an *action* using a mnemonic for each of it's methods.

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
    cli = ApplicationFactory('payroll', 'app.conf')
    cli.invoke()


if __name__ == '__main__':
    main()
```

The [ApplicationFactory] is the framework entry point that requires only one
parameter, which is the package distribution name and usually the name space of
the application.  Large organizations or projects prefix the string with their
name and the name is used in `setup.py` to resources that make up the package
distribution.

The second parameter is the [resource](config.html#resources) *application
context*, which as mentioned usually goes in the `resources` directory.
However, to keep things simple, ours points to a file in the root directory for
this example.  When we run this application from the command line using a help
flag (`--help`), we get:
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

We'll create a mock set of data directly in the `app.conf` file to go
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

**Note**: By default, only the subclass is used to generate the CLI.  If you
want to include the sub class for additional actions and options, set the class
attribute `CLASS_INSPECTOR` (see [INSPECT_META]) to `{}`.


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
same information as the [CONFIG_META] attribute.  The section name uses the
same section it *decorates* appended with `_decorates` in `app.conf`,
such as:
```ini
[app_decorator]
class_name = zensols.cli.ActionCli
option_excludes = set: db
```
which tells the framework to ignore the `db` field.  The [ActionCli] is the
framework's aforementioned plumbing that connects the class and method pair to
the command line.  Each `ActionCli` describes the class and at least one of
it's methods, each of which is an action with it's respective command line
metadata given as an [ActionMetaData].

The format of decorator sections can be modified with
`decorator_section_format` given to the [ActionCliManager].


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

The framework implements this user configuration injection with the
[ConfigurationImporter] class, which is just a data class with a method to load
the configuration and add it to the application context.  It is configured as a
*first pass* class, which means it is run before the application.


### Two Pass Command Line Parser

Generally speaking, there are many first pass actions that prepare for one of
many second pass actions indicated by the user using the *action*'s mnemonic.
The framework parses the command line parameters given by the user in two
passes:

1. The first pass parses options common to all applications and pertinent
   to tasks that usually prepare the environment before the application runs.
   Examples are configuring the log system with a debugging level, and in this
   example, loads the configuration.
   
   In this phase, all options from all methods are added so we can "fish out"
   the action mnemonic, which is the string used to indicate which method to
   run as we've seen with the `print_employees` method in the [application
   class](#application-class-and-actions) example
   
1. After the first pass completes, we know the action to run along with any
   other positional arguments given separated from the command line options.
   Now we know enough to build a new command line specialized for the *action*
   given by the user.

The [ConfigurationImporter] is both indicated it should run, and what file to
load with a `-c/--config` option followed by a file name.  Again, the this
option can be renamed with an [action decorator](#action-decorators), which
obviates its [CLASS_META](#ConfigurationImporter.CLASS_META) meta data.  Adding
this capability is as simple as adding it as an application:
```ini
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: config_cli, app

[config_cli]
class_name = zensols.cli.ConfigurationImporter
```

We've added the section `config_cli` to the list of sections to read, which
gives a definition for a new class of type [ConfigurationImporter], which in
turn adds the `-c` option:
```bash
Usage: main.py [options]:

Show all employees.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d, --dryrun          if given, don't do anything, just act like it
  -f <short|verbose>, --format=<short|verbose>
                        the detail of reporting
  -c FILE, --config=FILE
                        the path to the configuration file
```


### Split Out the User Configuration

Now we can move what we think the user might edit to the user context
`payroll.conf`, and we'll add a few defaults while we're at it:
```ini
[default]
age = 32
high_cost = 11.50

[bob]
class_name = domain.Person
age = ${default:age}
salary = 13.50

[homer]
class_name = domain.Person
age = 40
salary = 5.25

[human_resources]
class_name = domain.Department
name = hr
employees = instance: list: homer, bob
```

The `high_cost` user configuration option gives what the company determines is
a high cost employee and needs to be used to separate employees.


## Another Second Pass Action

Now we need to report on high salaried employees using the `high_cost` option
in the user configuration, so let's add that capability to the "database":
```python
@dataclass
class EmployeeDatabase(object):
    departments: Tuple[Department]
    high_cost: float

    @property
    def costly_employees(self) -> Iterable[Person]:
        return tuple(filter(lambda e: e.salary > self.high_cost,
                            chain.from_iterable(
                                map(lambda d: d.employees, self.departments))))
```

add access it from the main application data class `Tracker`:
```python
def report_costly(self):
    """Report high salaried employees."""
	emp: Person
	for emp in self.db.costly_employees:
		print(emp)
```

which now yields the following help usage:
```bash
Usage: main.py <printemployees|reportcostly> [options]:

Tracks and distributes employee payroll.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c FILE, --config=FILE
                        the path to the configuration file

Actions:
printemployees     show all employees
  -d, --dryrun                         if given, don't do anything, just act like it
  -f, --format <short|verbose>  short  the detail of reporting

reportcostly       report high salaried employees
  -d, --dryrun                         if given, don't do anything, just act like it
```

We now see an `Actions:` section, where we did not before.  Also notice the
application expects either `printemployees`, `reportcostly` as indicated in the
first usage line, and called *mnemonics*.  As mentioned, these are used as a
positional parameter by the user to invoke an *action* in the main class, which
for us, is in the `Tracker` class.

Before adding this method, we saw no mnemonics or action usage because there
was only a single second pass action given.  Since the framework had everything
it needed to know which method to run (the singleton of the class), it made all
input as a single set of options without requiring the action mnemonic.

Also note that the top level program documentation under the `Usage:` line
changed from:

`Show all employees.`

to

`Tracks and distributes employee payroll.`

This is because the framework can't decide between which method's documentation
to use since we have more than one eligible action, so instead it uses the
class's docstring.


### Renaming the Mnemonics

While the help messages look natural for a command line program, the long
mnemonic names look out of place and would be cumbersome to type.  Again, we'll
address this with the decorated [ActionCli] class by adding to the *decorated*
section:
```ini
[app_decorator]
class_name = zensols.cli.ActionCli
option_excludes = set: db
mnemonics = dict: {
    'print_employees': 'show',
    'report_costly': 'highcost'}
```
which has a new entry `mnemonics` as a `dict` with keys as method names and
mnemonics as values, which produces a better usage:
```bash
Usage: main.py <show|highcost> [options]:
...
Actions:
show         show all employees
  -d, --dryrun                         if given, don't do anything, just act like it
  -f, --format <short|verbose>  short  the detail of reporting

highcost     report high salaried employees
  -d, --dryrun                         if given, don't do anything, just act like it
```

Now we can in run the `report_costly` method with the `highcost` mnemonic and
user configuration file:
```bash
$ ./main.py -c payroll.conf highcost
Person(name='bob', age=32, salary=13.5)
```

Note that we now refer from the `Tracker` application's `emp_db` instance
reference in the application context file `app.conf` to the `human_resources`
`Department` section in the user configuration file `payroll.conf`.
Conversely, we link from the `default` section's `high_cost` parameter to the
"data base" `emp_db` section for the `EmployeeDatabase.high_cost` attribute.


### Default Action

A `default_action` attribute can be set on the [ActionCliManager] in the `cli`
section when it is created to use an action by name if the user does not supply
one.  Usage identifies which action is the default.


## Logging

It would be nice to be able to log some messages instead of print them for our
application, but only our application.  If we turn on information level logging
for the entire run time we could eventually get "polluting" logs that just
bury important information.  We could use the default Python logging system to
do this, and put our application logger in its own name space, then set the
level for that name space.  Here's the first part added to `payroll.py`:
```python
import logging
...
logger = logging.getLogger(__name__)
...
class Tracker(object):
...
logger.info(f'printing employees using format: {format}')
```

However, when we run the program, the print statement made in to a logging
statement won't be seen.  We need only to add a first pass action available in
the framework as the [LogConfigurator] added to the `cli` section of the
`app.conf` file.  Part of it's configuration, set as a data class field, is the
application logger name `payroll` for the `__name__` used in our code.  We
could add the name to the configuration, but then log messages would
mysteriously disappear if the file name was changed.  Instead, we make the
assumption the entire application is in the name space given by the
[setuptools] and refer to the name space by the package distribution meta data
we've already given in the `main.py` class.  This can be done with the
[PackageInfoImporter] class, which provides the name in a new section it
creates called `package` and refer to it from the [LogConfigurator] section:
```ini
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: config_cli, package_cli, log_cli, app
doc = A payroll program.

[package_cli]
class_name = zensols.cli.PackageInfoImporter

[log_cli]
class_name = zensols.cli.LogConfigurator
log_name = ${package:name}
```

Note that we must add the `package_cli` **before** the `log_cli` in the `apps`
option since they are processed in order and the log configurator needs the
`package` section created first.

We also add a `doc` option to the `cli` section to manually provide the
documentation since we now have more than one class, which doesn't allow for
taking it from the class docstring.


## More Actions

Speaking of the package, perhaps we want to report some information about it.
Already we have a way of getting it's version with the `--version` option.  But
we could print out, among other package meta data, the name.  Since it doesn't
seem to fit as a method in our employee tracking class, we'll add a new class
to `payroll.py`:
```python
@dataclass
class PackageReporter(object):
    config: Configurable

    def report(self):
        """Print package information."""
        name: str = self.config.get_option('name', section='package')
        print(f'package: {name}')
```

The `config` data class field is populated by the configuration factory that
created it with the configuration used to create it (see the [configuration]
documentation).  We then only need to report it's section's contents.

We'll add it to the list of applications:
```ini
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: config_cli, package_cli, log_cli, app, package_reporter

[package_reporter]
class_name = payroll.PackageReporter
```
which will register it as a second pass action, and thus a separate action and
mnemonic:
```bash
Usage: main.py <show|highcost|report> [options]:
...
report       print package information
```
and gives the same name of the package as provided in the `main`:
```bash
$ ./main.py report -c payroll.conf 
package: payroll
```


## Positional Arguments

Let's suppose our formatting for employee printing changes and we no longer
trust the default given on the command line.  Instead we want to force the user
to provide the format over specifying it as an option.  To do this, we only
need remove the default in the keyword argument making it a positional argument
in the method:
```python
def print_employees(self, format: Format):
	"""Show all employees.

	:param format: the detail of reporting

	"""
...
```
which shows up in the help usage as a positional argument rather than an option:
```bash
Actions:
show <format>     show all employees
  -d, --dryrun    if given, don't do anything, just act like it
```
and to run it:
```bash
./main.py show -c payroll.conf terse
INFO:payroll:printing employees using format: Format.terse
human_resources: homer, bob
```


## Environment

It is important to easily supply environment information to the application,
for which the framework has two means:

1. Provide environment variables using the [EnvironmentConfig] using the
   [import ini configuration](config.html#import-ini-configuration) as a
   section include.

1. Provide it directly to the [ApplicationFactory] in the `main.py` when we
   create it.

Any sophisticated application will probably involve both, so let's start with
the first, which is simply to add the following in the `app.conf`:
```ini
[import]
sections = imp_env

[imp_env]
type = environment
section_name = env
includes = set: HOME
```
which creates a new section `env` with the indicated environment variable
`HOME`.  We can add all variables if we don't provide `includes`, but some
variables that contain dollar signs confuse the `configparser.ConfigParser`
interpolation system.

Our application factory added to `main.py` includes:
```python
from dataclasses import dataclass
from pathlib import Path
from zensols.config import DictionaryConfig
from zensols.cli import ApplicationFactory


@dataclass
class PayrollApplicationFactory(ApplicationFactory):
    @classmethod
    def instance(cls: type, root_dir: Path = Path('.'), *args, **kwargs):
        dconf = DictionaryConfig(
            {'appenv': {'root_dir': str(root_dir)},
             'financial': {'salary': 15.}})
        return cls('payroll', 'app.conf', children_configs=(dconf,))


def main():
    cli = PayrollApplicationFactory.instance()
    cli.invoke()
```

This gives the application `appenv` and `financial` sections with data we
provide.  This is very handy in setting application roots that might have
different data directories for scientific data, models, etc.


## Directory Structure

So far, our examples have been small and had a simple flat directory
structure.  However, in larger applications, we'll want to branch out and
create a source directory tree and probably another for configuration.  Here
gives something simple, yet provides room for the application to grow:

* **root**
  * **resources**: contains files packaged in the distribution
    * **app.conf**: the application configuration
  * **etc**: user directory tree (any name works)
    * **payroll.conf**: user configuration
  * **mycom**: company module
    * **payroll**: our source app
	  * **domain.py**
	  * **payroll.py**

The final example provides this directory structure and provides a
comprehensive [example](#complete-examples) of the final product of this
tutorial.


## Conclusion

This tutorial was meant to instruct quickly on how to create applications.
There are many details and other features not covered, such as the listing
actions and documentation second pass action given in the last example.


## Complete Examples

See the [example] directory the complete code used to create the examples in
this documentation.  There is one directory for each sub heading in this
document, for example the [boilerplate](#boilerplate) section's steps are in
the `example/cli/1-boilerplate` directory in the source repository.


<!-- links -->

[example]: https://github.com/plandes/util/tree/master/example/cli
[configuration]: config.md
[setuptools]: https://setuptools.readthedocs.io/en/latest/

[Enum]: https://docs.python.org/3/library/enum.html
[OptionParser]: https://docs.python.org/3/library/optparse.html

[EnvironmentConfig]: ../api/zensols.config.html#zensols.config.envconfig.EnvironmentConfig
[ActionCli]: ../api/zensols.cli.html#zensols.cli.action.ActionCli
[ActionCliManager]: ../api/zensols.cli.html#zensols.cli.action.ActionCliManager
[ActionCliManager]: ../api/zensols.cli.html#zensols.cli.action.ActionCliManager
[ActionMetaData]: ../api/zensols.cli.html#zensols.cli.meta.ActionMetaData
[ApplicationFactory]: ../api/zensols.cli.html#zensols.cli.app.ApplicationFactory
[ConfigurationImporter]: ../api/zensols.cli.html#zensols.cli.lib.ConfigurationImporter
[ImportConfigFactory]: ../api/zensols.config.html#zensols.config.factory.ImportConfigFactory
[LogConfigurator]: ../api/zensols.cli.html#zensols.cli.lib.LogConfigurator
[PackageInfoImporter]: ../api/zensols.cli.html#zensols.cli.lib.PackageInfoImporter
[SimpleActionCli]: ../api/zensols.cli.html#zensols.cli.simple.SimpleActionCli
[CONFIG_META]: ../api/zensols.cli.html?zensols.cli.lib.LogConfigurator.CLI_META
[LogConfigurator.CONFIG_META]: ../api/zensols.cli.html?zensols.cli.lib.LogConfigurator.CLI_META
[INSPECT_META]: ../api/zensols.introspect.html?zensols.introspect.inspect.ClassInspector.INSPECT_META
