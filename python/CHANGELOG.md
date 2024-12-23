# Changelog

## [Unreleased]

### Added

- Papers can now generate citation reference strings via `to_citation()`.
  - Calling `to_citation()` without any arguments will produce ACL-formatted reference entries.
  - Alternatively, `to_citation()` can be called with the path to a CSL style file, in which case it will use citeproc-py to generate an entry formatted to the specifications in that style file.
- Papers can now generate brief markdown reference strings via `to_markdown_citation()`.
- PersonIndex now has function `find_coauthors_counter()` to find not just the identities of co-authors, but also get a count how many items they have co-authored together with someone.
- SIGIndex now reverse-indexes co-located volumes, so it is now possible to get SIGs associated with volumes, e.g. via `Volume.get_sigs()`.
- VenueIndex now reverse-indexes associated volumes, so it is now possible to get volumes associated with venues, e.g. via `Venue.volumes()`.
- Papers now have attribute `thumbnail`.
- Papers now have attribute `language_name`, which uses the [langcodes](https://langcodes-hickford.readthedocs.io/en/) library to map language tags in the XML to proper language names.
- Papers now have attributes `issue` and `journal` for edge cases where these are set on the paper level. `Paper.get_issue()` and `Paper.get_journal_title()` can be used to access them without having to know where they are defined.
- Volumes now have attributes `has_abstracts`, `venue_acronym`, and `web_url`.
- Names now have function `as_full()`, returning the full name in the appropriate format based on whether it is given in Han or Latin script.
- MarkupText now has function `as_xml()` to return a string of the internal XML representation.

### Changed

- `Venue.item_ids` and `Person.item_ids` are now lists instead of sets. This is because we need to preserve the order in which items were added when loading the XML, as this is meaningful (e.g. reflects the order in which items should appear on the Anthology website).
- `Paper.attachments` is now a list of tuples, instead of a dict. This is because attachment types are not always unique (e.g., there can be two "software" attachments).
- Bugfix: Events now use the correct URL template.
- Bugfix: Events that are both implicitly _and_ explicitly created now merge their information, instead of overwriting each other.
- Bugfix: Converting a `<texmath>` expression to Unicode no longer serializes the tail of the XML tag, but only the TeX math expression itself.
- Bugfix: Heuristic scoring of name variants will no longer overwrite canonical names that are explicitly defined in `name_variants.yaml`.
- Bugfix: In first names, the values `None` and `""` (empty string) are now considered equivalent.
- Bugfix: Name variants in different scripts are now correctly recorded as names for the respective author.
- Bugfix: `MarkupText.as_html()` now always correctly HTML-escapes characters.
- Bugfix: `MarkupText.from_xml()` now correctly handles empty tags; got converted to the string `"None"` before.

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
