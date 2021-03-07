# Configuration

This package provides advanced parsing of INI and YAML files that provide Java
Spring like mechanism to create in memory Python object instance graphs.  This
API also works with the [command line library](command-line.md) to easily
configure command line applications.

There are many configuration options and classes to choose from.  However, the
best place to start with the most functionality is the
[ExtendedInterpolationEnvConfig] class, which reads an [INI] substitution based
file.

This will read an [INI] format uses the `configparser.ExtendedInterpolation`
for [variable substitution].  See the [INI Format](#ini-format) section for an
example.

While the [INI] format is preferred, the [YAML] format is also supported.
Other formats (i.e. JSON) are easy to add by extending the [Configurable]
class.  See the [YAML Format](#yaml-format) section for more information.


## INI Format

The INI format is preferred because it is simple and has broad support as a
configuration parsing library in Python.  This format uses the syntax
`${section:name}` where `section` is the section name and `name` is the option
(variable name) settings.  For example `${default:temporary_dir}` refers to the
root directory's `target` directory.  The `root_dir` entry in the `default`
section is taken from an environment `dict` given in the initializer of the
[ExtendedInterpolationEnvConfig] class.

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

### Directory Based Path

The first parameter to all [INI] based configuration parser is either a file or
a directory.  If a file is given, only that file is read as configuration.  If
a directory is given, all files in the directory are read and parsed as if it
were one large configuration file and variable substitution works by cross
referencing between files with the same syntax as would be used in a single
file.


## YAML Format

This format is implemented by the [YamlConfig] class.  The [grsync] utility
provides an example [grsync YAML] configuration file.  The first level of all
properties are defined as sections.  However, all variables are accessible
using series of dot (`.`) separated paths.  See the YAML test
case [test_yaml.py] for an example.


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
(or storing) configuration.  Another reason for an application specific
configuration class is that the configuration is typically passed around the
application, and calling it by name can help the readability of your code.

The Python boilerplate generates this configuration class that defines faux
section called `env` as see in the `${env:app_root}` variable given in the
example from the [INI formatted] example.  This example shows how this default
environment is given (if not provided to the initializer).  The
`default_expect` parameter tells the parser to raise an error when a particular
parameter is not provided.


```python
from zensols.config import ExtendedInterpolationEnvConfig

class AppConfig(ExtendedInterpolationEnvConfig):
    def __init__(self, *args, **kwargs):
        if len(args) == 0 and 'config_file' not in kwargs:
            kwargs['config_file'] = 'resources/someproj.conf'
        if 'env' not in kwargs:
            kwargs['env'] = {}
        env = kwargs['env']
        defs = {'app_root': '.'}
        for k, v in defs.items():
            if k not in env:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'using default {k} = {v}')
                env[k] = v
        super().__init__(*args, default_expect=True, **kwargs)
```


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
* A string starting with `path:` parsed as a [pathlib.Path] instance.
* A string starting with `resource:` parsed as `path:`, but points to a
  resource path either locally, or from a `setuptools` installed package (see
  the [Resources](#resources) section).
* A string starting with `json:` parsed as standard JSON.
* A string staring with `eval:` parsed by the Python code reader (see the
  [Evaluation Parameters](#evaluation-parameters) section).
* A string starting with `instance:` an object instance (see the [Configuration
  Factory] and [Instance Parameters](#instance-parameters) sections).
* Anything else as a string.


### Configuration Factory

The configuration is parsed and given to an [ImportConfigFactory] to create
instances of objects.  Each instance is, by default, configured to create a
single instance of each object instance per section.  Once a class is
*referred* by name, the instance is looked up by the [ImportConfigFactory] and
created if it does not exist already per the [parsing](#parsing) rules.


Each section contains the data for an instance along with a option (variable)
entry `class_name`, which is the fully qualified class name (`<module>.<class
name>`).  Each option value contained in the respective section is set as an
attribute on the instantiated object instance.

For example, say you have the classes defined in a module called `domain`:
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
company: domain.Organization = factory('bob_co')

>>> bob
Person(age=56, aliases=['sideshow bob', 'Robert Underdunk Terwilliger Jr'])
>>> company
Organization(boss=Person(age=45))
>>> id(company.boss) == id(bob)
True
```

Parameters to the initialization method of the configuration factory indicate
whether to reload the module or not, which is the default.  This is
particularly hand when prototyping your code from a different module in the
Python REPL.


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

>>> school_clique
Organization(boss=Person(age=16, aliases=['cool dude (0)', 'bad dude (1)']))
```

### Resources

Resources are paths that exist either in a local project, or point to a
directory from a Python [setuptools] module.  This uses the [resource_filename]
method, which in turn, uses the [pkg_resources] API to base the path from an
installation.

This mechanism needs the package metadata information to find the correct
module in the install path.  This is set automatically when using CLI classes
such as [OneConfPerActionOptionsCliEnv].  However, there are additional
[setuptools] resources needed, which include:
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
fake_path = resource(zensols.someproj): resources/fake.txt
```


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

We then create the new *company* object and print with:
```python
senior_company: domain.Organization = factory('bobs_senior_center')

>>> senior_company
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

### Import INI Configuration

A more advanced feature is to import other configurations in a top level.  The
[ImportIniConfig] class also supports the [INI format](#ini-format), but adds
other configuration sections to its own.  To create a configuration file that
is used by the class, do the following:
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
sections = import_domain
references = imp_defaults

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
>>> homer's new age: 18
```


## Configuration Implementations

The list of configuration implementations that inherit from [Configurable] are
listed below:

* File based:
  * [IniConfig]: Application configuration utility in [INI
    format](#ini-format).  This reads from a configuration and returns sets or
    subsets of options/
  * [YamlConfig]: Parse configuration from [YAML files](#yaml-format).
  * [JsonConfig]: A configurator that reads [JSON](#json-format) as a two level
    dictionary.
  * [ImportIniConfig]: An [INI Configuration](#import-ini-configuration) that
    uses other [Configurable] classes to load other sections.
* Memory based:
  * [DictionaryConfig]: This is a simple implementation of a dictionary backing
    configuration.
  * [EnvironmentConfig]: An implementation configuration class that holds
    environment variables.
  * [StringConfig]: A simple string based configuration that takes a single
    comma delimited key/value pair string


## Complete Examples

See the [examples] directory the complete code used to create the examples in
this documentation.


<!-- links -->

[INI]: https://en.wikipedia.org/wiki/INI_file
[YAML]: https://yaml.org
[variable substitution]: https://docs.python.org/3.3/library/configparser.html#configparser.ExtendedInterpolation
[grsync]: https://github.com/plandes/grsync
[grsync YAML]: https://github.com/plandes/grsync/blob/master/test-resources/small-test.yml
[pathlib.Path]: https://docs.python.org/3/library/pathlib.html
[Java Spring]: https://spring.io
[setuptools]: https://setuptools.readthedocs.io/en/latest/
[pkg_resources]: https://setuptools.readthedocs.io/en/latest/pkg_resources.html

[test_yaml.py]: https://github.com/plandes/util/blob/master/test/python/test_yaml.py
[Configuration Factory]: #configuration-factory
[configuration factory]: #configuration-factory

[Configurable]: ../api/zensols.config.html#zensols.config.configbase.Configurable
[IniConfig]: ../api/zensols.config.html#zensols.config.iniconfig.IniConfig
[ImportIniConfig]: ../api/zensols.config.html#zensols.config.importini.ImportIniConfig
[DictionaryConfig]: ../api/zensols.config.html#zensols.config.dictconfig.DictionaryConfig
[EnvironmentConfig]: ../api/zensols.config.html#zensols.config.envconfig.EnvironmentConfig
[JsonConfig]: ../api/zensols.config.html#zensols.config.json.JsonConfig
[YamlConfig]: ../api/zensols.config.html#zensols.config.yaml.YamlConfig
[StringConfig]: ../api/zensols.config.html#zensols.config.strconfig.StringConfig
[ImportConfigFactory]: ../api/zensols.config.html#zensols.config.factory.ImportConfigFactory
[ExtendedInterpolationEnvConfig]: ../api/zensols.config.html#zensols.config.iniconfig.ExtendedInterpolationEnvConfig
[populate]: ../api/zensols.config.html#zensols.config.configbase.Configurable.populate
[resource_filename]: ../api/zensols.config.html#zensols.config.configbase.Configurable.resource_filename
[examples]: https://github.com/plandes/util/tree/master/example
[OneConfPerActionOptionsCliEnv]: ../api/zensols.cli.html#zensols.cli.peraction.OneConfPerActionOptionsCliEnv
