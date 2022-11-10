# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.1] - 2021-05-14
- Fixed install requires SQLAlchemy version

## [1.2.0] - 2021-03-31
- Added support of python 3.9
- Added support of SQLAlchemy 1.4
- Removed support of python 3.6
- Removed support of SQLAlchemy 1.1, 1.2

## [1.1.2] - 2020-10-21
- Fixed queries for UNIX platforms [issue-18]

## [1.1.1] - 2020-07-26
- Fixed deprecated time.clock [issue-16]

## [1.1.0] - 2020-06-29
- Removed support of python 2.7, 3.5
- Updated documentation
- Added code of conduct

## [1.0.3] - 2019-11-04
- Fixed an issue where concurrent calls to an API would cause "Profiling session has already begun" exception.

## [1.0.2] - 2019-04-06
### Changed
- Profiler stats type from `dict` on `OrderedDict`
### Fixed
- Readme examples imports from [@dbourdeveloper](https://github.com/dbourdeveloper)
- Profiler duplicates counter (now it's begin countig from `0`)

## [1.0.1] - 2019-04-04
### Added
- Human readable sql output to the console [@Tomasz-Kluczkowski](https://github.com/Tomasz-Kluczkowski)
- Py2 unicode support
- Docstring improvements

## [1.0.0] - 2019-03-25
### Added
- Supports for SQLAlchemy 1.3
- Makefile
- setup.cfg
- pep8 tox env
### Changed
- Set new GitHub username in the README
- Update setup requirements
### Fixed
- flake8 issues
### Removed
- Supports for SQLAlchemy 1.0
- .bumpversion (moved to setup.cfg)

## [0.5.0] - 2018-11-12
### Added
- Supports for SQLAlchemy 1.0, 1.1 and 1.2 versions

## [0.4.1] - 2018-11-08
### Fixed
- Report example image link in the README

## [0.4.0] - 2018-11-08
### Added
- README

## [0.3.4] - 2018-11-08
### Fixed
- Travis CI pipy provider secure password

## [0.3.2] - 2018-11-07
### Added
- Bump version config
- Travis CI deploy to pypi

## [0.3.1] - 2018-11-07
### Changed
- Travis CI python3.7 on python3.7-dev

## [0.3.0] - 2018-11-07
### Added
- TOX
- Setuptools configuration
- Support py2/py3
- Travic CI

## [0.2.0] - 2018-11-07
### Added
- Middleware tests and fixes
- Profiler tests and fixes
- Reporters tests and fixes
- Termcolors tests and fixes

## [0.1.0] - 2018-11-04
- Initial commit.
