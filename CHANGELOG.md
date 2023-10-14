# Changelog

## [Unreleased]

### Added

- ACL Anthology data can now be fetched automatically from Github, without the
  need to clone the repo manually.

## [0.4.0] — 2023-10-12

### Added

- Support for saving Anthology XML data, with full test coverage to ensure correctness.
- Support for saving Anthology JSON data for venues and SIGs.
  - This means that `name_variants.yaml` is the only Anthology metadata file
    that currently cannot be programmatically changed with this library.
- Support for Python 3.12.

### Changed

- `MarkupText.as_xml()` removed in favor of `.to_xml()`, with slightly different
  semantics.

## [0.3.0] — 2023-08-21

### Added

- Support for accessing SIG details.
- Support for accessing venue details.
- Basic support for accessing events, both explicitly defined and implicitly
  derived.
- Significant performance improvements for XML parsing and storing markup
  strings.

### Changed

- All "container" classes that wrap access by mapping IDs to objects now inherit
  from `SlottedDict`, which provides dictionary-like functionality.  For
  example, `CollectionIndex` is a container for `Collection` objects, which is a
  container for `Volume` objects, which is a container for `Paper` objects.  All
  functionality that works with dictionaries should work with these classes now,
  assuming IDs as keys and the wrapped objects as values.

## [0.2.1] — 2023-08-08

This can be considered the first release that has useful functionality,
including complete functionality for reading volumes, papers, and their
authors/editors.
