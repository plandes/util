# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]

### Changed
- Whether to print usage is optional when raising `ApplicationError` but
  default to no usage.
- Add feature to parse a variable number of arguments with `tuple` or
  `typing.Tuple`in application classes invoked from the command line.
- Fix single action conflicts with non-visible (in usage help specified with
  `is_usage_visible=False` in `CLI_META`) such as prototyping actions and
  `zensols.cli.harness.ConfigFactoryAccessor`.
- The `list` action is no longer a default in resource `cli-config.conf`.
- Add CLI artifact substitution (i.e. ``` :obj:`param_name` ``` becomes `-p`).


## [1.15.14] - 2025-11-26
### Added
- A `mkdir` flag to `std.stdout` to create non-existent parent directories when
  writing to files.

### Changed
- More configuration options and default settings for URLs and file names in
  class `Hasher`.
- Add more error reporting in `ClassInspector`.
- Fix class level for keyword `pass` during AST parsing.


## [1.15.13] - 2025-11-02
### Added
- Context manager `zensols.util.std.stdout` has a flag to create parent
  directories.

### Changed
- Fix `ast` "value" in `ClassInspector`.


## [1.15.12] - 2025-08-20
### Changed
- Fix `ast` Python 3.12 warning by removing 3.7 `str` type.
- The CLI `loglevel` option documentation was abbreviated.


## [1.15.11] - 2025-06-21
### Changed
- Switch to the `packaging` module for requirements parsing.
- Fixed "integration" tests.


## [1.15.10] - 2025-06-21
### Changed
- `CliHarness` system path index parameter.
- `Settings` uses parameter naming compatible with dictionaries.


## [1.15.9] - 2025-06-20
### Change
- Fix `Dictable` overriding `_write` method.
- Environment variable `ZENSOLSRC` can now be a path separated (`:` on UNIX) of
  directories to configuration files.


## [1.15.8] - 2025-05-15
### Changes
- Look for configuration files in a shared directory using the `ZENSOLSRC`
  environment variable.  See [ConfigurationImporter.get_environ_path].
- Fix `PackageResource` absolute path resources truncated leading slash removed
  bug.


## [1.15.7] - 2025-05-11
Switch from setuptools to [Pixi].

## Changed
- Move to [Pixi].
- Directory structure to match `pyproject.toml` conventions.


## [1.15.6] - 2025-03-22
### Added
- A time duration formatting utility (`DurationFormatter`).

### Changed
- Bug fix to `DictionaryConfig` option fetch.


## [1.15.5] - 2025-02-13
### Added
- A tolerant easy to use multiprocessing factory stash
  (`MultiProcessRobustStash`) that retries to create missing or failed items.


## [1.15.4] - 2025-02-12
### Changed
- Fix bug with missing `_initialized` attribute in Configurable subclasses.


## [1.15.3] - 2025-02-05
### Added
- A "shortcut" directive to get a section as a `dict` rather than
  `config.Settings`.


## [1.15.2] - 2025-01-25
### Added
- Support for Python 3.12.

### Changed
- Replace deprecated setuptools `pkg_resources` (removed in Python 3.12) with
  `importlib.{metadata,resources}`.


## [1.15.1] - 2025-01-23
### Changed
- Move `zensols.config.Writable` to `zensols.util`.  The class is still
  imported to the `zensols.config` module so import statements need not change.
- `zensols.util.Failure` extends from `zensols.util.Writable`.


## [1.15.0] - 2025-01-11
Additional feature additions to configuration. One of these feature additions
precludes support of Python 3.10.  All dependent packages can continue to use
1.14 as long as they do not serialize and instance of `Configurable`.  Support
for Python 3.12 will be added in a later version.

### Removed
- Drop support for Python 3.10.

### Changed
- Add an option to `LogConfigurator` to allow the application to configure the
  logging system while still leveraging this class.

### Added
- YAML configuration files now have the same importation capabilities as
  `ImportIniConfig`, but are experimental.
- `DictionaryConfig` provide a way to execute Python code with the `source`
  attribute.
- Feature to enable `ImportIniConfig` import sections predicated on a
  configured boolean.
- A monitor like the `open` function, but only closes the file-like object when
  necessary.


## [1.14.5] - 2024-10-14
### Added
- Access to the clipboard on macOS operating systems.
- Support for file name normalization (`FileTextUtil`) for non-ASCII
  and other special characters.
- A utility to find an executable in the `PATH` environment variable.

### Changed
- Command line usage gives the order of actions as they appear in the
  application case rather than alphabetically (now by default).  This can be
  configured to keep the alphabetic sort order.
- File or standard output `zensols.util.stdout` uses `None` instead of `+` to
  indicate to use a recommended file name for output rather than explicitly
  having to add as a file name.
- `StringConfig` takes a format that allows white space between commas as a
  regular expression.


## [1.14.4] - 2024-05-11
### Added
- Cached configurations using `ImportIniConfig`.
- Attribute access using the call directive (`call`).
- An LRU cache `Stash` class.
- A stash that filters `Failure`.

### Changed
- Confirm the naming of the `KeyLimitStash` class's attribute `n_limit` to
  `limit`.


## [1.14.3] - 2024-04-14
### Added
- A `TRACE` log level in `zensols.util.log`.

### Changed
- Add configuration evaluation and shell output to CLI show config (`config`)
  action.


## [1.14.2] - 2024-02-27
### Added
- Short usage and help synopsis using the short help option (`-h`).
- Application configuration aliases (`alias:`) as a solution to tricky
  configuration parser option interpolations.
- An application to clear file caches given a list of application configuration
  aliases.


## [1.14.1] - 2024-01-04
### Changes
- Fix `Failure` picking bugs.
- Move `Failure` and `APIError` to their own (`util.fail`) module.


## [1.14.0] - 2023-12-05
This release removes the deprecated CLI modules and is tested on Python 3.11.

### Added
- `UnitTester`, which runs unit test cases from the REPL for the rapid
  prototyping use case.
- Support for Python 3.11.

### Removed
- Old `actioncli` CLI modules `zensols.cli.{preaction,simple}`.
- Support for Python 3.9.


## [1.13.3] - 2023-11-29
### Changed
- `Failure` class is more flushed out.
- Documentation, flake8 warnings, typehints.


## [1.13.2] - 2023-09-30
### Add
- Functionality to force usage of the default action by argument reprocessing.

### Changed
- Default configuration searches UNIX style resource files for configuration
  (i.e. package `zensols.util` would point to `~/.zensols.util`).
- Harness CLI uses better shell parsing to create applications and resources.


## [1.13.1] - 2023-08-25
### Added
- Multiprocessing strategy (`Multiprocessor`) split from owning stash
  (`MultiProcessStash`).


## [1.13.0] - 2023-08-16
Moderate risk update release that changes tree structured application
configuration.

### Added
- Key subset stash class.
- A no-operation `Stash`.

### Changed
- Introduce a tree based `Configurable` for YAML and JSON type configurations.
- Fix YAML bug for empty configuration files.
- CLI `stdout` context manager is more CLI friendly.  Initial parameter is the
  same, but open arguments are now a list.
- Fix multi-processing stash by adding a call to `MultiProcessStash.prime`.
- Raise `ApplicationError`s from `ApplicationFailure`s.


### Added
- A new tree-like `Configurable` that allows for nested dictionary access
  previously only available in the `YamlConfig`.  This is now available in
  `DictionaryConfig` and `JsonConfig`.
- A new instance directive (``tree``) to create new instances from deep nested
  dictionary configuration.
- A decorator to catch an exception type and re-throw as an `ApplicationError`
  as a command line application convenience.
- Bug fix parsing empty YAML files.


## [1.12.6] - 2023-07-02
### Changed
- Fix the CLI app returned first pass action showing up in action list.


## [1.12.5] - 2023-06-11
### Added
- Integer selection parsing and CLI interaction.


## [1.12.4] - 2023-06-09
### Changed
- CLI bug fixes.


## [1.12.3] - 2023-06-07
### Added
- Jupyter notebook utility class `NotebookManager`.  This class integrates with
  access Zensols applications via Jupyter.
- Flexible module agnostic class resolution methods.

### Changed
- More comprehensive parsing of Python source files in `ClassInspector`.


## [1.12.2] - 2023-04-05
### Added
- Override all optional positional metadata.
- Configuration operand `application` to create instances of the context from a
  an external application.
- Create YAML from `Dictable` instances.
- A `Dictable` flat nested dictionary structure suitable for writing to JSON or
  YAML.
- A context manager that multiplexes between standard out or the file system.
- A byte formatting utility in `FileTextUtil`.

### Changed
- Refactor to uncouple configuration factory operands (i.e. `instance`,
  `object`) in `ImportConfigFactory` as separate classes.
- Allow overriding of positional metadata for the CLI package.
- Fix Sphinx API generated documentation and human readable documentation.


## [1.12.1] - 2023-02-02
### Added
- `CliHarness` application get method.


## [1.12.0] - 2023-01-22
### Added
- A programmatic method to get the config factory and application context using
  the CLI application invocation API from the `CliHarness`.  This uses an
  "invisible" application that returns the configuration factory enabling the
  application access without "short cutting" the API to get instances.
- An `instance:` parameter in application context configurations that allow
  new/deep instances.
- A convenience utility class `DefaultDictable` that provides access to methods
  such as `write` and `asjson` without needing inheritance.
- Command line help available on specified action only.

### Changed
- Upgraded the `configparser` package from 5.2 to 5.3.
- Fix bug with config factories throwing the wrong exception when using
  `type=import` in application configuration when using bad configuration files
  with `-c` on the command line.
- The `persisted` decorator and `PersistedWork` skip file system checks when
  configured as in memory rather with file system paths.
- The CLI `Cleaner` app now expands the user home directory when the syntax is
  provided with `pathlib.Path.expanduser`.
- Better command line help and usage formatting.


## [1.11.1] - 2022-09-30
A few functional `Stash` changes, but mostly a bug release.

### Added
- More options for file system name normalization.

### Changed
- Propagate clear method message in `FactoryStash`.
- Skip clear for read only stashes from `FactoryStash`.


## [1.11.0] - 2022-08-06
### Added
- Add a read-only zip file based stash.
- File system and hashing utilities.
- State clearing in `PersistableWork`.

### Changed
- Resource configuration (`conf_sec` for regular expressions).
- Better error messages from `DirectoryStash`.
- Robustly allow null YAML config values.

### Removed
- The `time` context manager removed the `logger` keyword parameter.


## [1.10.1] - 2022-06-15
### Changed
- Command line configuration metadata with configuration decorators bug fix.


## [1.10.0] - 2022-06-13
### Added
- Command line first pass applications and `--config` option added as resource
  libraries.
- If/then/else logic during configuration creation with
  `ConditionalYamlConfig`.
- Nest and invoke `--override` anywhere in the configuration importation
  list.
- Inline `@dataclasses` in YAML files at the section level.
- Scientific notation formatted configuration option values.

### Changed
- Updated documentation to be more current, added newer API.
- `DirectoryCompositeStash` now robustly handle group sequences.
- Better collapsing of long option and defaults usage help columns.
- Bug fixes and supporter for merging `CLI_META` for CLI applications.

### Removed
- Support for Python 3.8 is removed.


## [1.9.0] - 2022-05-14
### Removed
- Support for Python 3.7 is removed as `typing.get_origin` is needed by this
  version.

### Added
- Instances of `@dataclass` configurable in YAML configurables/files.

### Changed
- Make `DirectoryCompositeStash.groups` a property that re-configures the
  instance.
- By default YAML configurables use the root as the singleton section.


## [1.8.0] - 2022-05-04
### Added
- Feature to use configuration syntax resolution in evaluated configuration
  entries.
- Add option to `MultiProcessFactoryStash` to preemptively calculate data
  existence on a field parameter.
- Add `CacheFactoryStash` for read only stashes with a fixed key set that need
  a backing store.
- Command line application `CLI_META` combination useful for inheritance.
- Add log format setter to `LogConfigurator`.
- A YAML configuration importation class (`ImportYamlConfig`) like
  `ImportIniConfig`.

### Changed
- Ignore of single configuration file from `ImportIniConfig` bug fix.
- More robust error messages for `ImportIniConfig` reads.
- Better configuration `eval:` import support.


## [1.7.3] - 2022-02-12
### Changed
- Fixed delete and clear functionality in `ShelveStash`.
- Make `Settings` more dictionary like and inherit from `Dictable`.
- Move `DictResolver` and `ClassResolver` to introspection module.


## [1.7.2] - 2022-01-30
### Added
- The CLI class `EditConfiguration`, which edits the configuration file.
- The CLI class `ProgramNameConfigurator`, which adds the inferred program name
  as a section.

### Changed
- Section for `ActionCli` decorators over-write that which is defined at the
  class level for an application in `CLI_META`.
- Bug fixes for missing configuration when configured to not expect it.
- Remove need for the `class_name` in the `cli` section for application
  contexts.
- Remove need for the `cli` section, which defaults to loading the single
  application section `app`.


## [1.7.1] - 2022-01-12
### Changed
- Shelve extension calculation is not heuristically calculated by creating a
  file to fix tests across various (g)dbm libraries across platforms.
- Add file name in `persisted` to pickle error messages.
- Better `DirectoryStash` pickle error messages.
- Robustly ignore missing config files when the configuration importer is
  configured not to expect them.

### Added
- Simple CLI example.
- Class level properties set on `PersistableContainer` instances to
  automatically persist attributes.
- MacOS keychain `Configurable` for user/password access.
- `ImportConfigFactory` provides a way to create new instances with methods
  `new_instance` and `new_deep_instance`.


## [1.7.0] - 2021-10-22
### Added
- Added `frozendict` as a dependency.
- App config configuration have a new type (`import`), which allows a
  `^{config_path}` to be substituted with the `--config` file name giving more
  control over the start up load process.
- More harness/app factory convenience methods and functionality, such as
  creating a harness from the app factory.
- Jupyter harness is now reloadable.
- First pass applications return useful data, such as the `config` first pass
  app.

### Changed
- All options in the `import` section of `ImportIniConfig` must now be proper
  config data types, which are all lists prefixed with `list: `.
- Fixed argument splitting in `CliHarness`.
- Changed many cached `dict` to type `frozendict` to guard against
  unintentional modification of immutable data structures.


## [1.6.3] - 2021-10-03
### Changed
- `CliHarness` uses `LogConfigurator` to configure the logging system instead
  of `logging.basicConfig`.
- `OneShotFactoryStash` inherits from `PrimablePreemptiveStash` and uses its
  overridden methods to preempt data creation
- `CliHarness` is now more robust, and the default entry point class for large
  and small Python templates.

### Added
- Added Jupyter notebook harness.
- New CLI `ApplicationError` to differentiate between types of errors and
  when to print the stack trace by having the application factory handle the
  exception.


## [1.6.2] - 2021-09-21
### Changed
- CLI: configuration file option `--config` expected for list action.


## [1.6.1] - 2021-09-21
### Changed
- Fix option field mapping and JSON of CLI metadata for list app.
- Do not stringify class in `Dictable.asdict`.
- Move dump on load `Stash` to `PreemptiveStash` and create a
  `PrimablePreemptiveStash` to replace previously dual merged behavior.
- Fix entry point infinite loop call in multi-process in `CliHarness`.

### Added
- Positional documentation was added to metadata and list action app output.
- Add a `class:` configuration type to create new classes.
- Can now load resources on multiple config files in `ImportIniConfig`.


## [1.6.0] - 2021-09-07
### Changed
- Fix GitHub workflows continuous integration.
- Make private data structures that are private and subclass private
  respectfully: `Dealloc.ALLOCATIONS` and
  `PersistableContainer.PERSISTABLE_TRANSIENT_ATTRIBUTE`.
- Fix to `FactoryStash` for persisting `None` to file system instead of using
  the factory stash to create the item.
- When created instances with a `ConfigFactory`, attributes `name`, `config`
  and `config_factory` are only set when passed keyword arguments do not have
  them set.
### Removed
- Removed `zensols.util.Downloader`, which now is relocated to the
  [zensols.install] package.


## [1.5.3] - 2021-08-16
### Added
- A simple download with scroll bar utility class (`zensols.util.Downloader`).
- Additional logging.
- Speed `OneShotFactoryStash` by declaring worker type.

### Changed
- `DelegateStash` and `PreemptiveStash` now only calls the delegate `clear()`
  method when their `clear()` method.  This is a pretty big change since
  before, the delegate would call the super method to delete all data by key.
  This would chain from the `PreemptiveStash` to calculate where there is any
  data at all.  Now, the delegate is trusted to simply clear all data from the
  stash.
- Fixed empty INI error, and instead, return empty section set for empty INI
  files.


## [1.5.2] - 2021-08-07
### Added
- Class resolution in config factories.

### Changed
- Better de-allocation handling in de-allocation monitor.
- Shelve stash defaults to write back and auto close on, which is the expected
  and conforming behavior to most other stashes.


## [1.5.1] - 2021-06-29
### Changed
- Switch to raw `IniConfig` as default in config factory for `ini` extension
  files from the `ImportIniConfig`.  This simplifies when using with an
  `ImportIniConfig`, reduces substitution dependencies and suites most use
  cases.  In most cases, it's the `ImportIniConfig` using this setting, which
  ends up doing the string interpolation after everything is imported, thus
  creating less start up configuration read issues.
- Shelve stash auto closes between client invocations.

### Added
- Use caught errors in application CLI to generate error messages, including
  missing configuration files.
- Allow CLI configuration importer to set the type of importer.
- Resource de-allocation added to multi-processing stashes.
- Resource de-allocation added to application CLI.
- Resource de-alloocation keywords added to `persisted` and `PersistedWork`.


## [1.5.0] - 2021-04-29
### Changed
- Follow the same pattern with mnemonics as options: includes/excludes.  The
  `mnemonics` action attribute has changed to `mnemonic_overrides`.  Both
  `mnemonic_includes`, `mnemonic_excludes` are now optional to more easily
  select mnemonics in the CLI application class.
- Better CLI application usage and support.
- Upgraded PyYAML library for security fix.
- Better `ImportIniConfig` option dependency handling support.
- More conventional capitalized messages for raised errors.
### Added
- Multi-processing factory stash.
- Support for single process stash creation (set `workers=1`).
- More typehints and documentation.
- New error class hierarchy.
- Backward 3.7 compatibility abstract syntax tree compatibility for
  `ClassInspector`.
- Support for overriding configuration in application CLI.


## [1.4.1] - 2021-03-10
### Changed
- Bug fix release: enumeration mapping for CLI.


## [1.4.0] - 2021-03-05
### Added
- A new command line generated from configurables, configuration factories and
  the meta data of `dataclass`s.
- Tutorial based documentation for the new introspection based command line
  system.
### Removed
- Old (simple) command line documentation.


## [1.3.3] - 2021-02-17
### Added
- A new `Configurable` class that imports using other `Configurable` classes:
  `ImportIniConfig`.
- A new environment based configuration that can be loaded by
  `ImportIniConfig`.
- Configuration can now *quote* with a string prefix.
- Configuration can parse lists and create instances of tuple, lists and
  dictionaries.

### Changed
- `ClassResolver` moved to `zensols.config` to be used by the new
  `ImportIniConfig`.


## [1.3.2] - 2021-02-13
### Removed
- Remove unused `StashMapReducer` and `FunctionStashMapReducer` since they are
  obviated by `MultiProcessStash`.

### Added
- Type hints added to wrapped methods using `@persisted`.
- `Writable` plays better with `Dictable` using `write`.
- Anonymous object instances (using `Settings`) used for configuration with
  given class (`class_name`) property.
- Basic test case for `MultiProcessStash`.
- Instance graphs in documentation.

### Changed
- Inline `dataclass` documentation and reference fixes.


## [1.3.1] - 2021-01-12
### Changed
- Add sections support to `zensols.config.YamlConfig` and other compatibility
  with super class.
- Fix tests for Python 3.9.
- Copy forward documentation from decorators, so `@persisted` (for example)
  fields generate Sphinx documentation.


## [1.3.0] - 2020-12-09
Major release.

### Added
- In depth top level documentation, including sphinx/API linked docs.
- New `Dictable` creates dictionaries working with `dataclasses` and
  automatically human (more or less) readable using `Writable`.
- Much more documentation, both at the API level and top level `README.md` and
  in `./doc`, which now gets compiled in to sphinx docs.
- Support for creation of `pathlib.Path` from configuration.
- Support for resources from configuration with transparent `pathlib.Path`
  creation as either installed or run from source tree.
- Configuration environment section.
- More test cases for existing and new classes.
- Add class metadata "explorer".

### Changed
- Default for `zensols.config.ImportConfigFactory.shared` is `True`.
  **Important:** this is a big change, so it would be prudent to retest your
  dependent code.
- Finalize `Writable` interface and change dependent code.
- Fixes to deallocation and resource clean up.
- Refactored configuration files by purpose and class with better class
  hierarchy.
- Refactored stash files by purpose and classes.
- Better more stable `DelegateStash` attribute resolution handling.


## [1.2.5] - 2020-05-23
### Added
- API and framework Sphinx documentation.


## [1.2.4] - 2020-05-23
### Changed
- Better logging.

### Added
- `Writable` abstract class used to as an object oriented pretty print based
  API.
- Delegate attribute: flag to pass messages to the delegate.
- Class space defaults set for delegate attribute.


## [1.2.3] - 2020-05-10
### Added
- Meta data walker with class level annotation to better debug stash instance
  graphs.
- `Writable` interface that provides a basic multi-line indention specific
  pretty print.
- More unit tests for stashes and increased coverage in other areas.

### Changed
- Use `testall` to invoke all unit tests.  Standard `test` tests all but the
  *time* specific unit tests.
- More robust configuration reloading strategy.


## [1.2.2] - 2020-05-05
### Changed
- Better documentation.
- Fix reload module for `ImportConfigFactory` on `reload=True`.
- Pass parameters and optionally reload by parameters in `instance` directive
  in configuration files.
- Update super method call style (Python 3.7 at least).
- Make consistent pretty print naming.

### Removed
- CLI stubs.
- Removed the `ConfigFactory` class.  Use `ImportConfigFactory` is its place.

### Added
- Persistable work injections.
- Evaluation statements in configuration now allow for local imports.
- `ImportConfigFactory` shares in memory instances across configuration sections.


## [1.2.1] - 2020-04-26
### Changed
- Fix nested modules not importing.


## [1.2.0] - 2020-04-24
### Added
- Initial version.


<!-- links -->
[Unreleased]: https://github.com/plandes/util/compare/v1.15.14...HEAD
[1.15.14]: https://github.com/plandes/util/compare/v1.15.13...v1.15.14
[1.15.13]: https://github.com/plandes/util/compare/v1.15.12...v1.15.13
[1.15.12]: https://github.com/plandes/util/compare/v1.15.11...v1.15.12
[1.15.11]: https://github.com/plandes/util/compare/v1.15.10...v1.15.11
[1.15.10]: https://github.com/plandes/util/compare/v1.15.9...v1.15.10
[1.15.9]: https://github.com/plandes/util/compare/v1.15.8...v1.15.9
[1.15.8]: https://github.com/plandes/util/compare/v1.15.7...v1.15.8
[1.15.7]: https://github.com/plandes/util/compare/v1.15.6...v1.15.7
[1.15.6]: https://github.com/plandes/util/compare/v1.15.5...v1.15.6
[1.15.5]: https://github.com/plandes/util/compare/v1.15.4...v1.15.5
[1.15.4]: https://github.com/plandes/util/compare/v1.15.3...v1.15.4
[1.15.3]: https://github.com/plandes/util/compare/v1.15.2...v1.15.3
[1.15.2]: https://github.com/plandes/util/compare/v1.15.1...v1.15.2
[1.15.1]: https://github.com/plandes/util/compare/v1.15.0...v1.15.1
[1.15.0]: https://github.com/plandes/util/compare/v1.14.5...v1.15.0
[1.14.5]: https://github.com/plandes/util/compare/v1.14.4...v1.14.5
[1.14.4]: https://github.com/plandes/util/compare/v1.14.3...v1.14.4
[1.14.3]: https://github.com/plandes/util/compare/v1.14.2...v1.14.3
[1.14.2]: https://github.com/plandes/util/compare/v1.14.1...v1.14.2
[1.14.1]: https://github.com/plandes/util/compare/v1.14.0...v1.14.1
[1.14.0]: https://github.com/plandes/util/compare/v1.13.3...v1.14.0
[1.13.3]: https://github.com/plandes/util/compare/v1.13.2...v1.13.3
[1.13.2]: https://github.com/plandes/util/compare/v1.13.1...v1.13.2
[1.13.1]: https://github.com/plandes/util/compare/v1.13.0...v1.13.1
[1.13.0]: https://github.com/plandes/util/compare/v1.12.7...v1.13.0
[1.12.7]: https://github.com/plandes/util/compare/v1.12.6...v1.12.7
[1.12.6]: https://github.com/plandes/util/compare/v1.12.5...v1.12.6
[1.12.5]: https://github.com/plandes/util/compare/v1.12.4...v1.12.5
[1.12.4]: https://github.com/plandes/util/compare/v1.12.3...v1.12.4
[1.12.3]: https://github.com/plandes/util/compare/v1.12.2...v1.12.3
[1.12.2]: https://github.com/plandes/util/compare/v1.12.1...v1.12.2
[1.12.1]: https://github.com/plandes/util/compare/v1.12.0...v1.12.1
[1.12.0]: https://github.com/plandes/util/compare/v1.11.1...v1.12.0
[1.11.1]: https://github.com/plandes/util/compare/v1.11.0...v1.11.1
[1.11.0]: https://github.com/plandes/util/compare/v1.10.1...v1.11.0
[1.10.1]: https://github.com/plandes/util/compare/v1.10.0...v1.10.1
[1.10.0]: https://github.com/plandes/util/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/plandes/util/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/plandes/util/compare/v1.7.3...v1.8.0
[1.7.3]: https://github.com/plandes/util/compare/v1.7.2...v1.7.3
[1.7.2]: https://github.com/plandes/util/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/plandes/util/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/plandes/util/compare/v1.6.3...v1.7.0
[1.6.3]: https://github.com/plandes/util/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/plandes/util/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/plandes/util/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/plandes/util/compare/v1.5.3...v1.6.0
[1.5.3]: https://github.com/plandes/util/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/plandes/util/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/plandes/util/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/plandes/util/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/plandes/util/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/plandes/util/compare/v1.3.3...v1.4.0
[1.3.3]: https://github.com/plandes/util/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/plandes/util/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/plandes/util/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/plandes/util/compare/v1.2.5...v1.3.0
[1.2.5]: https://github.com/plandes/util/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/plandes/util/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/plandes/util/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/plandes/util/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/plandes/util/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/plandes/util/compare/v0.0.0...v1.2.0


[zensols.install]: https://github.com/plandes/install
[Pixi]: https://pixi.sh
[ConfigurationImporter.get_environ_path]: https://plandes.github.io/util/api/zensols.cli.lib.html#zensols.cli.lib.config.ConfigurationImporter.get_environ_path
