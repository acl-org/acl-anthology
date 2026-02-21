# Changelog

## [Unreleased]

### Added

- Files (such as paper PDFs) can now be downloaded from their remote URLs via `.download()`.
- Added `.get_namespec_for(Person)` on papers and volumes, to more easily find the NameSpecification referring to a given Person.
- Added `Person.namespecs()` to iterate over all NameSpecifications referring to this Person.
- Added `NameSpecification.normalize()` to heuristically fix casing and match spelling details to known canonical names. This is mainly intended for ingestion and called automatically when using `create_paper()`/`create_volume()`.

### Changed

- Switched tooling from Poetry to uv, and from Black to Ruff formatter.
- Renamed `PersonIndex.resolve_namespec` to `_resolve_namespec` to discourage external use.
- Improvements to Names and NameSpecifications:
  - `Name.slugify()` now treats typographic apostrophes (U+02BC and U+2019) the same as regular ones.
  - NameSpecifications now track if they have been modified, and will trigger their parent collection being saved on `Anthology.save_all()`.
  - NameSpecifications can now be resolved via `NameSpecification.resolve()`. Therefore, `Anthology.resolve()` has been deprecated.

## [1.0.0] — 2026-01-24

This release implements the new [name resolution and author ID logic](https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan), and is therefore fundamentally incompatible with ACL Anthology data before the switch to this new system.

### Added

- Support for Python 3.14.
- Anthology now provides `save_all()` to conveniently save all data files.  The library tracks modifications to collection objects to only write XML files that have actually changed.  (Tracking changes does not work on _every_ possible modification, though; see the documentation.)
- `Anthology.from_within_repo()` can be used to quickly instantiate the Anthology from within its own repo.
- Person:
  - Now provides `orcid`, `degree`, `disable_name_matching`, and `similar_ids` fields that correspond to the respective fields in the new `people.yaml`.
  - Changing `id`, `orcid`, `names`, or using `add_name()` or `remove_names()` will now automatically update the PersonIndex.
  - Added `change_id()` that updates a person's ID on all of their connected papers.
  - Added `make_explicit()` that makes all necessary changes to change an implicit ("/unverified") to an explicit Person.
  - Added `merge_with_explicit()` that makes all necessary changes to move an implicit ("/unverified") person's papers/volumes to an explicit Person.
- PersonIndex:
  - Now also indexes Person objects by ORCID, and provides `by_orcid` and `get_by_orcid()`.
  - Now also keeps a mapping of name slugs to (verified) person IDs, via `slugs_to_verified_ids` (mostly for internal use).
  - Added `ingest_namespec()` to implement the [matching logic on ingestion](https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan#ingestion) of new volumes.
  - Added `PersonIndex.create` to instantiate a new Person and add it to the index.
- MarkupText now provides a `from_()` class method that calls the appropriate builder method, using heuristic markup parsing if instantiated from a string.
- MarkupText now supports some common string methods, such as `__contains__`, `endswith`, `startswith`.
- Venues can now be created via `VenueIndex.create()`.

### Changed

- Several breaking changes to PersonIndex for the new author ID system:
  - Loading the index now expects a `people.yaml` file instead of `name_variants.yaml`.
  - Renamed `get_or_create_person()` to `resolve_namespec()` and refactored it to reflect the [new name resolution logic](https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan#proposed-name-resolution-logic).
  - Renamed `name_to_ids` to `by_name`, in line with the new `by_orcid` field.
  - Changed the type of exceptions that can be raised; `AmbiguousNameError` was replaced by `NameSpecResolutionError` and `PersonDefinitionError`.
  - Changed the previously experimental `save()` function to serialize the `people.yaml` file.
- Person now stores names as tuples of `(Name, NameLink)`, the latter of which indicates if the name was explicitly defined in `people.yaml` or inferred by the name resolution logic (e.g. via slug matching).  As a consequence, `Person.names` can no longer be modified in-place; use `Person.add_name()`, `Person.remove_name()`, or the setter of `Person.names`.
- Setting a canonical name for a Person changed from `.set_canonical_name()` to `Person.canonical_name = ...`
- Attributes that expect a MarkupText, such as `Volume.title` or `Paper.abstract`, can now be set to a string, in which case the string will be automatically converted to MarkupText, including markup parsing.
- EventLinkingType renamed to EventLink.
- Refactored verbosity handling and progress/log output.  This fixes a bug where empty lines would appear in stdout from Rich's progress bars, even if they were disabled with `verbose=False`.  If stdout is not a TTY, progress/log output will be written to stderr instead.  If stderr is not a TTY, progress bars will be suppressed by default.

### Removed

- Support for "Papers with Code" references has been removed, as the service has been discontinued in August 2025.

## [0.5.4] — 2025-11-27

This release only exists to provide necessary functionality for transitioning to the [new author ID system](https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan).

### Added

- NameSpecification now provides an `orcid` field.

### Changed

- Updated the XML schema to match the data folder.

## [0.5.3] — 2025-06-22

This release adds more functionality for ingesting new proceedings and modifying existing data.

### Added

- Collections now use a minimal-diff algorithm when saving back to XML, ensuring that `save()` can be called without generating unnecessary changes in the XML files.
- MarkupText can now be instantiated from strings (potentially) containing LaTeX markup.
  - This reimplements functionality used at ingestion time previously found in `bin/latex_to_unicode.py`.
- Paper objects now have a `type` attribute indicating if they are frontmatter, backmatter, or a regular paper.
  - This adds support for the `<paper type="backmatter">` attribute that was previously ignored, and slightly refactors how frontmatter is identified, making it more explicit rather than just relying on the paper ID.
- Paper now exposes `<mrf>` elements, currently only used in a single collection, as "attachments" of type "mrf".

### Changed

- Event: `colocated_ids` has changed from listing VolumeIDs to listing tuples of `(VolumeID, EventLinkingType)`, where EventLinkingType now makes clear if the association between the VolumeID and the Event was inferred or explicitly defined in the XML (in a `<colocated>` block).
- MarkupText: Typographic quotes now convert to/from LaTeX quotes more consistently.
- Names: Fixed some inconsistencies where `<first/>`, `<first></first>`, and a missing "first" tag would not be considered fully equivalent (within `Name` and `utils.xml.assert_equals`).
- Paper attachments without a type attribute in the XML now give their type as an empty string (instead of defaulting to "attachment"), in order to be able to reconstruct whether there was an explicit type attribute or not.
- Made `utils.xml.assert_equals` more robust and added some explicit tests for it.
  - Fixed a bug where `utils.xml.assert_equals` did not take into account that the relative order of some XML tags matters, e.g. `<author>` or `<editor>`, and would still consider them equal if those were reordered.
- Made `utils.xml.indent` more robust to a few edge cases.

## [0.5.2] — 2025-05-16

This release adds support for Python 3.13 and initial functionality for creating new proceedings.

### Added

- Support for Python 3.13.
- Papers are now indexed by their bibkeys and can be retrieved via `Anthology.get_paper_by_bibkey()`.
- Bibkeys can now be generated and updated, guaranteeing uniqueness.
- Collections, Volumes, Papers, and Events can now be newly created with functions on their respective parent objects.
  - Event creation currently has some unintuitive behaviour due to the existence of implicit event creation and linking; see docs.
- FileReferences can now be instantiated from files, and functions for checksum computation have been added.

## [0.5.1] — 2025-01-02

This release changes the PyPI package name from acl-anthology-py to acl-anthology.

### Added

- VenueIndex can now set `no_item_ids=True` to skip reverse-indexing volumes. This avoids parsing all XML files if all you want to access is basic venue information, but means that `Venue.item_ids` will be empty. _You probably don't want to use this unless you know that you are not going to need this information._

### Changed

- LaTeX encoding now uses [pylatexenc](https://pylatexenc.readthedocs.io/) instead of latexcodec, and wraps all macros in braces. This should address problems with BibTeX handling, see [#4280](https://github.com/acl-org/acl-anthology/issues/4280).

## [0.5.0] — 2024-12-25

This release is intended to be feature-complete with regard to generating the entire ACL Anthology website.

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
