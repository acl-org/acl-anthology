# Copilot Instructions for ACL Anthology

## Python Library (`acl_anthology`)

- Only use **public API** methods from the `acl_anthology` library. Never call private methods (those starting with `_`).
- Read the library documentation under `python/docs/` before writing code that uses the library.
- The online docs are at https://acl-anthology.readthedocs.io/

## Key API patterns

- Load the Anthology: `Anthology(datadir=...)` or `Anthology.from_within_repo()`
- Access volumes: `anthology.get_volume("2025.acl-main")`
- Access papers: `anthology.get_paper("2025.acl-main.1")`
- Create papers: `volume.create_paper(title=..., authors=..., **kwargs)` — this handles case normalization, ORCID ingestion, and person indexing automatically.
- Resolve authors: `anthology.people.get_by_namespec(namespec)` (not `_resolve_namespec`)
- Parse IDs: `from acl_anthology.utils.ids import parse_id`
- Case protection: use `fixedcase.protect.protect()` on XML title elements
- Save changes: `collection.save()`

## People index

- Call `anthology.people.load()` before creating papers if you need author resolution (matching names to known persons).
- Author names use `NameSpecification` wrapping a `Name` object.
- aclpub2 format uses `first_name`/`last_name`; the library uses `first`/`last`.
