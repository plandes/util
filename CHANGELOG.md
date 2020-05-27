# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]
### Changed
- Default for `zensols.config.ImportConfigFactory.shared` is `True`.
  **Important:** this is a big change, so it would be prudent to retest your
  dependent code.


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
[Unreleased]: https://github.com/plandes/util/compare/v1.2.5...HEAD
[1.2.5]: https://github.com/plandes/util/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/plandes/util/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/plandes/util/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/plandes/util/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/plandes/util/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/plandes/util/compare/v0.0.0...v1.2.0
