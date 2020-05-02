# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]


### Changed
- Better documentation.
- Fix reload module for `ImportConfigFactory` on `reload=True`.
- Pass parameters and optionally reload by parameters in `instance` directive
  in configuration files.
- Update super method call style (Python 3.7 at least).
- Make consistent pretty print naming.

### Removed
- CLI stubs.
- `Removed the `ConfigFactory`` class.  Use ``ImportConfigFactory`` is its place.



## [1.2.1] - 2020-04-26
### Changed
- Fix nested modules not importing.


## [1.2.0] - 2020-04-24
### Added
- Initial version.


<!-- links -->
[Unreleased]: https://github.com/plandes/util/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/plandes/util/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/plandes/util/compare/v0.0.0...v1.2.0
