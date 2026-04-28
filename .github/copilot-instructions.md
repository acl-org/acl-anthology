# Copilot Instructions for ACL Anthology

## Python Library (`acl_anthology`)

- Only use **public API** methods from the `acl_anthology` library. Never call private methods (those starting with `_`).
- Read the library documentation under `python/docs/` before writing code that uses the library.
- You should never parse XML directly; always use the library
- The online docs are at https://acl-anthology.readthedocs.io/

## Key API patterns

- Load the Anthology: ideally using `Anthology.from_within_repo()`
- Access volumes: `anthology.get_volume("2025.acl-main")`
- Access papers: `anthology.get_paper("2025.acl-main.1")`
- Create papers: `volume.create_paper(title=..., authors=..., **kwargs)` — this handles case normalization, ORCID ingestion, and person indexing automatically.
- Resolve authors: `anthology.people.get_by_namespec(NameSpecification)`, `anthology.people.get_by_name(Name)`, or `anthology.people.get_by_orcid(orcid)`
- Case protection: use `fixedcase.protect.protect()` on XML title elements
- Save changes: `anthology.save_all()`

## People index

- Author names use `NameSpecification` wrapping a `Name` object.
- aclpub2 format uses `first_name`/`last_name`; the library uses `first`/`last`.

## Important scripts in `bin/`

These may be useful as references for how the library works.

- `bin/ingest.py` — Ingests new proceedings into the Anthology.
- `bin/create_hugo_data.py` — Builds the website data.
- `bin/generate_crossref_doi_metadata.py` and `bin/add_dois.py` — Add DOIs to ingested volumes.
- `bin/add_revision.py` — Adds revisions by reading from structured input.

One-time transition scripts go under `bin/oneoff/`.
