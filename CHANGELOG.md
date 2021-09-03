# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]
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
[Unreleased]: https://github.com/plandes/util/compare/v1.5.3...HEAD
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
