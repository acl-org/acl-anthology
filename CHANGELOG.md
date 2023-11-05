# Changelog

## [Unreleased]

## [0.4.3] — 2023-11-05

### Added

- Papers and volumes can now generate their BibTeX entries via `to_bibtex()`.  Currently, a volume's BibTeX entry is simply the BibTeX entry of its frontmatter.  (This mirrors how the old library handles it.)
- Volumes now provide `get_journal_title()` to fetch the journal title from the venue metadata if it's not explicit set.
- Papers now have attributes `bibtype` and `web_url`.
- Collections now provide `validate_schema()` to validate their XML source files against the library's RelaxNG schema.

### Changed

- A frontmatter entry now no longer inherits `authors` from the parent volume's editors.
- Bugfix: `parse_id()` now parses old-style frontmatter IDs correctly.

## [0.4.2] — 2023-10-21

### Added

- Lots of documentation, including a web-hosted version.
- Many new convenience functions, such as `Anthology.get_person()`, `Anthology.find_people()`, `Volume.get_events()`, `Person.papers()`, `Person.volumes()`.

### Changed

- Showing progress bars (i.e. `verbose=True`) is now the default.
- Shorter `repr()` output for many classes, sacrificing detail for better usability in interactive settings.
- `Person` objects now require a pointer to the Anthology instance.
- Bugfix: EventIndex didn't reverse-index co-located volumes.

## [0.4.1] — 2023-10-14

### Added

- ACL Anthology data can now be fetched automatically from Github, without the
  need to clone the repo manually.

### Changed

- Fixed an encoding problem when running on Windows.

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
