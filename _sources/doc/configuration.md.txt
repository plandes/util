# Configuration

This package provides advanced parsing of INI, YAML and JSON files that provide
[Java Spring] like mechanism to create in memory Python object instance graphs.
This API also works with the [command line library](command-line.md) to easily
configure command line applications.

The configuration system uses [ImportIniConfig] and [ImportConfigFactory] to
load, parse, and construct application objects from structured configuration
resources. [ImportIniConfig] handles INI-style configuration files and supports
layered, multi-resource configurations, while [ImportConfigFactory] is
responsible for instantiating configured objects based on that parsed
configuration.

Using [ImportIniConfig], you specify one or more configuration resources (for
example, files on disk, classpath resources, or open streams).
[ImportYamlConfig] is the analogue for configuration chaining as discussed in
the [YAML section](#yaml-format).  Once parsed, that configuration is passed to
[ImportConfigFactory] to construct application components and objects by
name. This combination provides a clean and extensible mechanism for handling
structured configurations in your application.


## Configuration File Loading Order

When an application uses the Zensols CLI infrastructure with
[ConfigurationImporter], configuration is resolved from multiple sources in a
defined precedence order. This order determines how overlapping or duplicate
configuration properties are merged, with later sources overriding earlier
ones.

The typical configuration loading order is as follows:

1. **Command-Line Configuration** Attempt to load the configuration specified
   by the ``--config`` command-line option.

2. **Environment Variable Configuration Path** If the ``--config`` option is
   not provided, attempt to resolve the configuration path from an environment
   variable (see :meth:`get_environ_var_from_app`).  For example, for the
   package ``zensols.util``, the ``UTILRC`` environment variable is consulted
   for the configuration file path.

3. **User Home Resource File** If the environment variable is not defined, look
   for a UNIX-style resource file in the user’s home directory (see
   :meth:`get_environ_path`).  For example, the package ``zensols.util``
   resolves to ``~/.utilrc``.

4. **ZENSOLSRC Search Path** If the home directory resource file
   (``~/<app>rc``) is not found, all paths specified in the ``ZENSOLSRC``
   environment variable are searched.  Multiple paths may be specified and must
   be separated by the operating system path separator (i.e. `:` under
   UNIX/Linux).

5. **Child Configuration Load** Load the *child* configuration, which
   represents the resolved configuration from the previously discovered source.

6. **Configuration Merge** Copy all sections from the child configuration,
   allowing discovered configuration values to override existing defaults.
   
This layered approach ensures that *configuration settings are deterministic*,
with user and command-line preferences taking precedence over application and
library defaults. By structuring configuration sources in this order, you can
supply broad defaults in code while empowering users and integrators to adjust
behavior without modifying source or packaged resources.

See the API documentation for [ConfigurationImporter] for more details on how
these sources are combined and how priority is determined in your specific CLI
application.


## INI Format

The INI format is preferred because it is simple and has broad support as a
configuration parsing library in Python.  This format uses the syntax
`${section:name}` where `section` is the section name and `name` is the option
(variable name) settings.  For example `${default:temporary_dir}` refers to the
root directory's `target` directory.  The `root_dir` entry in the `default`
section is taken from an environment `dict` given in the initializer of the
[ExtendedInterpolationEnvConfig] class.  For example:
```ini
[default]
root_dir = ${env:app_root}
temporary_dir = ${root_dir}/target
resources_dir = ${root_dir}/resources
results_dir = ${root_dir}/results

[app]
class_name = zensols.someproj.app.MainApplication
path = path: ${default:temporary_dir}/app.dat
```

Note that user home relative directories are interpolated with
[os.path.expanduser], for example:
```ini
[app]
class_name = zensols.someproj.app.MainApplication
path = path: ~/app.dat
```
may be used to store the `app.dat` file in the user's home directory.


### Directory Based Path

The first parameter to all [INI] based configuration parser is either a file or
a directory.  If a file is given, only that file is read as configuration.  If
a directory is given, all files in the directory are read and parsed as if it
were one large configuration file and variable substitution works by cross
referencing between files with the same syntax as would be used in a single
file.


## YAML Format

The [YAML](https://yaml.org) format is implemented by the [YamlConfig] class.
The [grsync] utility provides an example [grsync YAML] configuration file.  The
first level of all properties are defined as sections.  However, all variables
are accessible using series of dot (`.`) separated paths.  See the YAML test
case [test_yaml.py] for an example.


### YAML sections

YAML configuration files "fit" in the INI configuration two level (section,
option) constraints by indicating nodes in the YAML tree as sections and the
respective children nodes as that section's options.  A list of sections can be
given as a node under the root called `sections`.  For example, the YAML
configuration file:
```yaml
project:
  sections: [project.context]
  context:
    example: nlparse
```
is equivalent to:
```ini
[project.context]
example = nlparse
```

When the `sections` node is missing, then all root level nodes in the YAML are
sections with children nodes as respective options, so the YAML:
```yaml
project: example: nlparse

context:
  default: someproj
```

has the INI equivalent as:
```ini
[project]
example = nlparse

[context]
default = someproj
```

### YAML Importation

Much like [INI importation](#import-ini-configuration), the [ImportYamlConfig]
class supports importation with an `import` node.  For example:
```yaml
project:
  import:
    some_yaml_imp:
      config_file: an-ini-file.conf
  example: nlparse
```
with `an-ini-file.conf` containing:
```ini
[an_imported_sec]
child_op = 1
```
is equivalent to:
```ini
[project]
import = dict: {'some_yaml_imp': {'config_file': 'a.conf'}}
example = nlparse

[an_imported_sec]
child_op = 1
```


### YAML Conditionals

Simple if/then/else logic can be used in YAML configurations using a top level
`condition` node with children `if`, `then` and `else` nodes using the
[ConditionalYamlConfig] class.  However, the following caveats apply:
* Only a single node can follow under the `if`, `then` and `else` nodes.
* The same node name must used under the `then` and `else` nodes.
* All `if` `then` and `else` node must always exist.

When the `if` node evaluates to any "truthy" value, the child under the `then`
node replaces everything at and under the respective `condition` node,
otherwise `else` node is used as the replacement.

The `condition` node can appear anywhere and at any level in the YAML tree.
However, to avoid the issue of name collisions as sections, a prefix can be
added, such as:

For example, the [conditional YAML test case] has:
```yaml
1.condition:
  if: 'eval: not ${default:testvar}'
  then:
    top_lev:
      bval: falseval
  else:
    top_lev:
      bval: trueval

3.condition:
  if: ${default:testvar}
  then:
    classify_net_settings:
      embedding_layer: 'glove_50_embedding_layer'
  else:
    classify_net_settings:
      embedding_layer: 'transformer_embedding_layer'
```
In this example, the `default:testvar` is defined either elsewhere in this
configuration or defined by a "calling" [INI
imported](#import-ini-configuration) section.


## JSON Format

This format is implemented by the [JsonConfig] class.  It reads JSON as a two
level dictionary.  The top level keys are the section and the values are a
single depth dictionary with string keys and values

A caveat is if all the values are terminal, in which case the top level
singleton section is `default_section` given in the initializer and the
section content is the single dictionary.


## Inversion of Control

This package provides a [Java Spring] like *inversion of control* system with
one major difference: this API strives to be as simple as possible and
integrate with all other *zensols* packages.


## Application Context

Any non-trivial application is recommended to have an *application context*
type class that allows for specific customization and behavior with retrieving
(or storing) configuration.  This framework uses instances of [Configurable]
for this application context, which is added to instances created by a
[ConfigFactory] (including [ImportConfigFactory], which is the API framework
default).  It populates classes that have the following *initial* parameters in
the initializer in order:

* `name`: the name of the section from which the instance was created
* `config`: the [Configurable] *application context* where instance was defined
* `config_factory`: the [ConfigFactory] that created the instance


### Parsing

The [Configurable] class defines access methods to the configuration data,
including how to get primitives (`get_option_*` methods) or populate a hash or
class from a section's data ([populate]).  The latter method is sophisticated
in how it reads data, which uses the following rules:
* Any string of numbers (i.e. `5839202`) as an integer
* A string of numbers with a single decimal point (i.e. `3.123`) as a float.
* Either `True` or `False` parsed as a boolean.
* A string starting with `str:` parsed as a string.  This is a way to *quote* a
  string.
* A string starting with `list:` or `tuple:` parsed as a comma delimited string
  with optional space around each element.
* A string starting with `asdict:` sets the entries in a section as a
  dictionary (see the [Dictionary Sections](#dictionary-sections) section.
* A string starting with `path:` parsed as a [pathlib.Path] instance.
* A string starting with `resource:` parsed as `path:`, but points to a
  resource path either locally, or from a `setuptools` installed package (see
  the [Resources](#resources) section).
* A string starting with `json:` parsed as standard JSON.
* A string staring with `eval:` parsed by the Python code reader (see the
  [Evaluation Parameters](#evaluation-parameters) section).
* A string starting with `instance:` as an object instance (see the
  [Configuration Factory] and [Instance Parameters](#instance-parameters)
  sections).
* A string starting with `alias:` that indirectly points to an instance to
  instantiate like `instance:` (see [Aliases](#aliases)).
* A string starting with `object:` as an object specified by class name (see
  the [Configuration Factory] and [Instance Parameters](#instance-parameters)
  sections).
* A string starting with `class:` as a class/type specified by a class name.
* A string starting with `dataclass(<class name>)` as a dataclass (see
  [Dataclasses](#dataclasses)).
* A string starting with `application` as an application context (see
  [Applications](#applications)).
* A string starting with `call` as a Python method invocation (see
  [Calls](#calls)).
* A string starting with `tree` as a Python method invocation (see
  [Tree](#tree)).
* Anything else as a string.


### Configuration Factory

The configuration is parsed and given to an [ImportConfigFactory] to create
instances of objects.  Each instance is, by default, configured to create a
single instance of each object instance per section.  Once a class is
*referred* by name, the instance is looked up by the [ImportConfigFactory] and
created if it does not exist already per the [parsing](#parsing) rules.

Each section contains the data for an instance along with a option (variable)
entry `class_name`, which is the fully qualified class name (`<module>.<class
name>`).  When this entry is missing, the section is instantiated as a `dict`
like object as detailed in [dictionary sections](#dictionary-sections).

Each option value contained in the respective section is set as an attribute on
the instantiated object instance.  For example, say you have the classes
defined in a module called `domain`:

```python
from typing import List
from dataclasses import dataclass


@dataclass
class Person(object):
    age: int
    aliases: List[str]


@dataclass
class Organization(object):
    boss: Person
```

We can define instances of these objects in an [INI formatted] file
`domain.conf` as such:
```ini
[default]
age = 56

[bob]
class_name = domain.Person
age = ${default:age}
aliases = eval: ['sideshow bob', 'Robert Underdunk Terwilliger Jr']

[bob_co]
class_name = domain.Organization
boss = instance: bob
```

Next, we can create and access by creating the configuration with the file
name, and using the configuration from an [ImportConfigFactory]:
```python
from zensols.config import ExtendedInterpolationEnvConfig, ImportConfigFactory
import domain

factory = ImportConfigFactory(ExtendedInterpolationEnvConfig('obj.conf'))
bob: domain.Person = factory('bob')
print(bob)
company: domain.Organization = factory('bob_co')
print(company)
print(id(company.boss) == id(bob))
```

output:
```console
Person(age=56, aliases=['sideshow bob', 'Robert Underdunk Terwilliger Jr'])
Organization(boss=Person(age=45))
True
```

Parameters to the initialization method of the configuration factory indicate
whether to reload the module or not, which is the default.  This is
particularly hand when prototyping your code from a different module in the
Python REPL.


### Dictionary Sections

Sections that have no `class_name` that are instantiated using entries with
`instance:` are created as [Settings] objects.  These instances act in a Python
dictionary manner and can be converted to `dict` instances with `asdict`.

While the [Settings] class has the advantage of accessing configuration entries
as both by index (`obj['key']`) but also by attribute (`obj.key`), it is
sometimes desirable to use a `dict` without having to call `asdict`.  To
accomplish this, simply change the class used as an [evaluation
parameter](#evaluation-parameters) such as:

```ini
[bart]
class_name = domain.Person
age = 16

[school_attendance]
bart_info = instance({'param': {'class_name': 'builtins.dict'}}): bart
```


### Evaluation Parameters

Instance options (or any configuration section's options) can be created with
an evaluation that allows for importing modules.  For example, if we want to
use the `itertools` package by providing a counting for an alias, we could
have:
```ini
[bart]
class_name = domain.Person
age = 16
aliases = eval({'import': ['itertools as it']}):
    list(map(lambda x: f'{x[0]} dude ({x[1]})',
         zip('cool bad'.split(), it.count())))
```
Note that the Python code in the `eval` is multi-line.

We then create the new *company* object and print with:
```python
school_clique: domain.Organization = factory('school_clique')
print(school_clique)
```
output:
```console
Organization(boss=Person(age=16, aliases=['cool dude (0)', 'bad dude (1)']))
```

Along with the `import` keyword, you can also use `resolve` in use the same
configuration parsing functionality create and resolve instances, then use it
in the evaluation.  For example:
```ini
dictionary_of_paths = eval(
  {'resolve': {'ent_file': 'resource(example.package): resources/config.json'}}): {
   'path': ent_file}
```
creates a dictionary with a `pathlib.Path` instance for key `path` set to the
resources directory with a JSON file of installed package `example.package`.


### Resources

Resources are paths that exist either in a local project, or point to a
directory from a Python [setuptools] module.  This uses the [resource_filename]
method, which in turn, uses the [pkg_resources] API to base the path from an
installation.

This mechanism needs the package metadata information to find the correct
module in the install path.  However, there are additional [setuptools]
resources needed, which include:
* `python-resources` added in `PROJ_MODULES` in the makefile using the
  `zenbuild` build environment
* `package_data` in `src/python/setup.py` to include the globs for the
  resources you want to include (`package_data={'': ['*.txt']}` for the example
  below).

An example of a resource path, which finds the file `fake.txt` in the local
project's directory `resources` is:
```ini
fake_path = resource: resources/fake.txt
```

In case the program isn't automatically configured with the module to find the
resource, you may add it in the configuration declaration itself.  For example,
if our [setuptools] name is `zensols.someproj`, configure the resource as:
```ini
fake_path = resource(zensols.someproj): resources/obj.txt
```


### Resource Libraries

Resource libraries are just a collection of configuration files that are deployed with a
library and accessible when that library is installed.  These are useful when a
lot of configuration is needed to make a library useful, such as the [Zensols
deep learning natural language processing library].  The convention if to have
a top level `obj.conf` for the package that imports everything else that is
needed.  For example, to import the [zensols.deepnlp resource library] use:
```ini
[import]
sections = list: imp_conf

[imp_conf]
type = importini
config_files = list: resource(zensols.nlp): resources/obj.conf
```
The `type = importini` tells it to use a [ImportIniConfig] (see the [Configuration
Implementations](#configuration-implementations) section).  This parameter can
also be set to `import` to use [ImportIniConfig] for `.conf` and `.ini` files,
and [ImportYamlConfig] for `.yml` files.

The `type` directive in import sections is not needed as long as standard
extensions are used.  However, if they are not, or specialized configurations
are desired, use the `type_map` directive to map extensions to configuration
implementations.  For example, the following maps `.yml` files to
[ConditionalYamlConfig] and `.conf` to [ImportIniConfig] implementations.
```ini
type_map = dict: {'yml': 'condyaml', 'conf': 'importini'}
```
You can also use `type = import` to automatically choose the importation
variant configuration implementation for each extension.

For an example of how to use a resource library, see the [nlparse example].


### Instance Parameters

Instances can take parameters to substitute values.  This is useful when you
want to define the values of an instance in the parent.  Extending from the
example given in the [configuration factory] section, we can define a person's
age in the company object with:
```ini
[bobs_senior_center]
class_name = domain.Organization
boss = instance({'param': {'age': 69}}): homer
```

A shorthand using `object:` and specifying the class name inline is useful in
cases where you don't want to create an additional section and/or don't want to
share the instance (see [shared instance memory
space](#shared-instance-memory-space)).  The equivalent configuration for not
sharing the `homer` object is:
```ini
[bobs_senior_center]
class_name = domain.Organization
boss = object({'param':
                 {'age': 69,
                  'aliases': ['Homer', 'Homer Simpson']}}):
         domain.Person
```

We then create the new *company* object and print with:
```python
senior_company: domain.Organization = factory('bobs_senior_center')
print(senior_company)
```
output:
```console
Organization(boss=Person(age=69, aliases=['Homer', 'Homer Simpson']))
```

Lists, tuples and dictionaries can be used with instance parameters as well.
Simply use the prefix `list:`, `tuple:` or `json:` (with a dictionary) as
described in the [parsing](#parsing) section.  Now we'll add another field,
which are a tuple of employees referring to two other sections in the
configuration file:
```ini
[bobs_senior_center]
class_name = domain.Organization
boss = instance({'param': {'age': 69}}): homer
employees = instance: tuple: bob, bart
```


### Shared Instance Memory Space

The [configuration factory] by default shares all instances in memory provided
by `instance:` entries using the lazy load method.  When these are encountered,
the factory looks to see if the instance has been created, and returns shared
references to those that already have.

This can be turned off by settings `shared = False` to the [ImportConfigFactory
initializer], but in most cases this is called by other framework code.  Other
ways to create new instances in separate memory spaces are to use the
[new_instance] method in your calling client instead of [instance], but even
this does not address how to create separate instances in the [application
context](#application-context).

For this, a special `share` parameter can be provided in the `instance:` entry
clause to use the aforementioned methods to create the new instance.  There are
three methods, which include:

* `default`: [instance] which uses the factory instance's `shared`
  initializer parameter to indicate whether to create shared instances,
* `evict`: [new_instance] which returns the current instance in the
  shared space (if there is one), then immediately evicts that instance,
* `deep`: [new_deep_instance] which creates a new object graph, all of which
  will have a completely new memory space, regardless of the shared space
  state.

For example:
```ini
[larrys_senior_center]
class_name = domain.Organization
boss = instance({'share': 'deep'}): homer
```
creates a new instance of `homer` that is not shared with `bobs_senior_center`.


### Aliases

There are occasions where defining which [instance](instance#parameters) to use
can depend on previously defined configuration, which can be done with the
typical configuration parser `${}` syntax.  However, this does not work when
this configuration is not yet defined like in CLI application contexts where
subordinate values are defined afterward.  To accommodate this, the following
syntax can be used:

```ini
alias[(<parameters>)]: <section>:<option>
```

For example, the `instance:` syntax:
```ini
[fruit_default]
name = fruit

[fruit]
class_name = app.Banana
color = yellow

[basket_instance]
class_name = app.Basket
fruit = instance: ${fruit_default:name}
```
is equivalent to:
```ini
[basket_instance]
class_name = app.Basket
fruit = alias: fruit_default:name
```


### Dataclasses

Instances of [dataclasses](https://docs.python.org/3/library/dataclasses.html)
are supported using a `dataclass(<class name>): <section>` form.  Either use a
`dict:` prefix in INI files, or define it in YAML with the corresponding
(recursive data class) structure.  For example, the [dataclass test case] the
following:
```yaml
croot:
  instances:
    dept: 'dataclass(test_yaml_dataclass.Department): croot.referenced.dept'
  referenced:
    dept:
      name: hr
      employees:
        - name: bob
          age: 21
          salary: 15.5
        - name: jill
```
Creates a dataclass instance of `test_yaml_dataclass.Department` whose
definition is given with configuration starting with `dept:`.  Inline
dataclasses in are also supported by creating a `dataclass: <class name>` entry
with the following caveats:
* It must be in a YAML configuration file.
* It must be defined as a section (see [YAML sections](#yaml-sections)).


### Applications

Application contexts of other installed Zensols applications can be accessed in
a completely separate memory space.  This creates a new application context
using a [CliHarness] and sets the property to the value of the instance of the
given section name.  For example, if we have an installed payroll application,
we can access it with:
```ini
[conglomerate]
business1 = application(zensols.payroll): larrys_senior_center
```
This has the advantage over importing applications using resource libraries
since the application context is set up and configured how it is meant to be as
a standalone application.  This is essential when using applications with paths
pointing to large trained ML models.


### Calls

*Callables* and methods on Python object instances created in the application
context can be used to set values.  The parameters and the instance are given,
such as:
```ini
[tracker]
class_name = payroll.Tracker

[employees]
db = call({'param': {'method': 'print_employees', 'format': 'short'}}): tracker
```
This sets the `db` parameter on the `employees` instance to the return value of
the tracker's `print_employees` method.  The remaining parameters are passed to
the method, which is `format = short` in this example.

The `method` parameter may be omitted if the referenced instance is *Callable*,
but the curly braces are needed in the parenthesis (i.e. `call({})`).  Instead
of calling a method, an attribute or property is accessed by replacing `method`
with `attribute`.


### Tree

Deep nested dictionaries for hierarchical data can also be used to create new
instances of objects.  A section name, dot separated path to the data and
optionally additional parameters to create the instance are provided.  For example:
```yaml
instance:
  employee: >-
    tree({'param': {'name': 'data.person',
                    'age': 25}}): data
data:
  person:
    class_name: Person
    name: Paul
    age: 23
    deep_record:
      more:
        nodes: here
```

Creates an instance of `Person` overriding the `age` parameter.  See the
`tree.py` in the [examples] for the full source code.


### Import INI Configuration

A more advanced feature is to import other configurations in a top level.  The
[ImportIniConfig] class also supports the [INI format], but adds other
configuration sections to its own.  To create a configuration file that is used
by the class, do the following:
1. Create an `import` section that has:
   * `sections`: a comma delimited list of sections with information of other
     configuration to load
   * `references`: a comma delimited list other sections to include while
     resolving information in the loaded sections.
2. For each listed in `sections`, create a section with the corresponding name
   with the following:
   * `type`: this is the type of configuration, which can be one of `ini`,
     `yaml`, `json` or `string`.  For more information, look up the
     corresponding implementation (i.e. for `yaml` look at [YamlConfig]).
   * `class_name`: this can be used in place of `type` to give a full qualified
     class name (i.e. `zensols.config.YamlConfig`).
   * `config_file`: is needed for all file system based configurations.
     However this varies and specific to the initializer parameter set of the
     indicated class.  For example for [StringConfig], `config_str` is needed.
	 
The `references` section list is needed to *bootstrap* the configuration so it
has all the data necessary to substitute.  For example, if you have a defaults
section with a directory location, that section is necessary if you want to
substitute a path (see the [import_factory example](#complete-examples)).

In most cases, parameter substitution (using `${}`) will work both forwards and
backwards, meaning that configuration is available in the child configurations
to the parent and vice versa.  The same goes one child's configuration to
another.  However, import order is important so put those referenced
configuration first in the order.

To continue our [person](#instance-parameters) example, we'll create a import
configuration with almost identical information, but we'll remove the default
section so we can see parameters substituted in the child from the parent.
```ini
[imp_defaults]
age = 22
dom_path = obj.conf

[import]
sections = list: import_domain
references = list: imp_defaults

[import_domain]
type = ini
config_file = path: ${imp_defaults:dom_path}
```

First we reference `imp_defaults` so `config_file` in `import_domain` get the
full path to the child configuration file.  This loads `obj.conf`, which is the
same file we used before.  However, it has a new section we didn't use before,
which is:
```ini
[bobs_youth_center]
class_name = domain.Organization
boss = instance({'param': {'age': ${imp_defaults:age}}}): homer
employees = instance: tuple: bob, bart
```

This section looks like the previous one, except now we set Homer's age to
`${imp_defaults:age}`, which is set in the parent `imp.conf` (see [examples]).

**Tip**: you can use `resource:` to point to configuration files included in
your wheel/egg that define the more involved object instantiating as to avoid
*polluting* the top level configuration the user sees.

As before, we create the factory and use it to create the `company` object:
```python
from zensols.config import ImportIniConfig, ImportConfigFactory
import domain

factory = ImportConfigFactory(ImportIniConfig('imp.conf'))
company: domain.Organization = factory('bobs_youth_center')
print(f"homer's new age: {company.boss.age}")
```
output:
```console
homer's new age: 18
```


## Configuration Implementations

The list of configuration implementations that inherit from [Configurable] are
listed below:

* File based:
  * [IniConfig]: Application configuration utility in [INI
    format](#ini-format).  This reads from a configuration and returns sets or
    subsets of options (`type_map = ini`).
  * [YamlConfig]: Parse configuration from [YAML files](#yaml-format)
    (`type_map = yml`).
  * [JsonConfig]: A configurator that reads [JSON](#json-format) as a two level
    dictionary (`type_map = json`).
  * [ImportIniConfig]: An [INI Configuration](#import-ini-configuration) that
    uses other [Configurable] classes to load other sections (`type_map = importini`).
  * [ImportYamlConfig]: like [ImportIniConfig] but more limited in
    functionality using the YAML format (see [YAML
    Importation](#yaml-importation)) (`type_map = importyaml`).
  * [ConditionalYamlConfig]: like [ImportYamlConfig] but replaces (sub)trees in
    the YAML configuration based on simple if/then/else logic (see [YAML
    Conditions](#yaml-conditions)) (`type_map = condyaml`).
* Memory based:
  * [DictionaryConfig]: This is a simple implementation of a dictionary backing
    configuration.
  * [EnvironmentConfig]: An implementation configuration class that holds
    environment variables.
  * [StringConfig]: A simple string based configuration that takes a single
    comma delimited key/value pair string.


## Complete Examples

See the [examples] directory the complete code used to create the examples in
this documentation.


<!-- links -->

[INI]: https://en.wikipedia.org/wiki/INI_file
[YAML]: https://yaml.org
[variable substitution]: https://docs.python.org/3.3/library/configparser.html#configparser.ExtendedInterpolation
[grsync]: https://github.com/plandes/grsync
[grsync YAML]: https://github.com/plandes/grsync/blob/master/test-resources/yaml-test.yml
[pathlib.Path]: https://docs.python.org/3/library/pathlib.html
[Java Spring]: https://spring.io
[setuptools]: https://setuptools.readthedocs.io/en/latest/
[pkg_resources]: https://setuptools.readthedocs.io/en/latest/pkg_resources.html
[os.path.expanduser]: https://docs.python.org/3/library/os.path.html#os.path.expanduser

[Zensols deep learning natural language processing library]: https://github.com/plandes/deepnlp
[zensols.deepnlp resource library]: https://github.com/plandes/deepnlp/tree/master/resources
[nlparse example]: https://github.com/plandes/nlparse/blob/master/example/simple.py

[test_yaml.py]: https://github.com/plandes/util/blob/master/test/python/test_yaml.py
[Configuration Factory]: #configuration-factory
[configuration factory]: #configuration-factory
[INI format]: #ini-format
[INI formatted]: #ini-format

[Settings]: ../api/zensols.config.html#zensols.config.serial.Settings
[Configurable]: ../api/zensols.config.html#zensols.config.configbase.Configurable
[IniConfig]: ../api/zensols.config.html#zensols.config.iniconfig.IniConfig
[ImportIniConfig]: ../api/zensols.config.html#zensols.config.importini.ImportIniConfig
[DictionaryConfig]: ../api/zensols.config.html#zensols.config.dictconfig.DictionaryConfig
[EnvironmentConfig]: ../api/zensols.config.html#zensols.config.envconfig.EnvironmentConfig
[JsonConfig]: ../api/zensols.config.html#zensols.config.json.JsonConfig
[YamlConfig]: ../api/zensols.config.html#zensols.config.yaml.YamlConfig
[ImportYamlConfig]: ../api/zensols.config.html#zensols.config.importyaml.ImportYamlConfig
[ConditionalYamlConfig]: ../api/zensols.config.html#zensols.config.condyaml.ConditionalYamlConfig
[StringConfig]: ../api/zensols.config.html#zensols.config.strconfig.StringConfig
[ConfigFactory]: ../api/zensols.config.html#zensols.config.facbase.ConfigFactory
[ImportConfigFactory]: ../api/zensols.config.html#zensols.config.importfac.ImportConfigFactory
[ImportConfigFactory initializer]: ../api/zensols.config.html#zensols.config.importfac.ImportConfigFactory.__init__
[instance]: ../api/zensols.config.html#zensols.config.importfac.ImportConfigFactory.instance
[new_instance]: ../api/zensols.config.html#zensols.config.importfac.ImportConfigFactory.new_instance
[new_deep_instance]: ../api/zensols.config.html#zensols.config.importfac.ImportConfigFactory.new_deep_instance
[ConfigurationImporter]: ../api/zensols.cli.lib.html#zensols.cli.lib.config.ConfigurationImporter
[CliHarness]: ../api/zensols.cli.html#zensols.cli.harness.CliHarness
[ExtendedInterpolationEnvConfig]: ../api/zensols.config.html#zensols.config.iniconfig.ExtendedInterpolationEnvConfig
[populate]: ../api/zensols.config.html#zensols.config.configbase.Configurable.populate
[resource_filename]: ../api/zensols.config.html#zensols.config.configbase.Configurable.resource_filename
[examples]: https://github.com/plandes/util/tree/master/example
[dataclass test case]: #https://github.com/plandes/util/blob/master/test-resources/dataclass-test.yml
[conditional YAML test case]: https://github.com/plandes/util/blob/master/test-resources/config-conditional.yml
