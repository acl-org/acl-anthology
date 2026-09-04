# AGENTS.md

## Repository overview

This repository contains the authoritative data and code for the ACL Anthology,
a library of scientific publications.  This repo includes:

1. **Authoritative metadata** in `data/`: XML paper/volume metadata
   (`data/xml/*.xml`, one file per "collection", e.g. a conference/year) and
   JSON indices for people, venues, and SIGs (`data/json/`).
2. **Static website templates/assets** in `hugo/`: the templates/assets used to
   render https://aclanthology.org/ from the data above via the Hugo static site
   generator <https://gohugo.io/>.
3. **Scripts** in `bin/`: build scripts used during website generation, scripts
   invoked by Github action workflows, and scripts used manually by maintainers
   of the library (e.g. ingestion, fixups, report generation).
4. **Python library** in `python/`: the `acl_anthology` Python library
   (published to PyPI) that parses, models, and writes the data files. This is a
   separate `uv` workspace member with its own `pyproject.toml`, tests, and
   justfile, and instructions in `python/AGENTS.md`.

The Python workspace is managed by `uv`.  Dependencies needed by scripts in
`bin/` go in root-level `pyproject.toml`.

## Commands

Root level (site generation, whole-repo checks):

```bash
just check               # test-scripts + XML tab check + pre-commit --all-files
just build               # build the full Hugo website into build/anthology (expensive!)
just serve               # build in development mode and run `hugo server`
uv run bin/ingest.py -h  # run any bin/ script (uv resolves deps automatically)
```

Only build the website when explicitly requested, as this is very time- and
memory-intensive.

For commands related to the Python library, see `python/AGENTS.md` or `just -l
python`.

## Content changes always go through the library

For modifications or bugfixes concerning the authoritative `data/` directory,
**never parse `data/xml/*.xml` or `data/json/*.json` directly** — always use the
`acl_anthology` Python library (`python/`), whether writing a one-off `bin/`
script or fixing a bug. Only use its **public API** (nothing starting with `_`).

Read docstrings, `python/AGENTS.md`, and `python/docs/`
before writing code against the library if unfamiliar with it. In particular,
`python/docs/guide/modifying-data.md` contains comprehensive recipes for author
and person management (e.g. `make_explicit()`, setting ORCIDs, and disambiguation).

### Key API patterns

- Load the Anthology from scripts run inside this checkout, working on the authoritative metadata in `data/`:

   ```python
   from acl_anthology import Anthology
   anthology = Anthology.from_within_repo()   # auto-discovers repo root
   ```

- Access collections, volumes, and papers:

   ```python
   anthology.get_collection("2025.acl")
   anthology.get_volume("2025.acl-main")
   anthology.get_paper("2025.acl-main.1")
   ```

- Create collections, volumes, and papers by going through `create_` commands.
  For example, create a new paper by calling `Volume.create_paper()`, **never**
  by instantiating `Paper()` directly — this handles case normalization, ORCID
  ingestion, person indexing etc. automatically.

- Find and resolve authors:

   ```python
   anthology.get_person(person_id)              # by ID
   anthology.people.get_by_namespec(name_spec)  # or get_by_name(), get_by_orcid()
   ```

- Save changes via `anthology.save_all()`. This will only save files that need
  to be modified.

- `fixedcase.protect.protect()` should be applied to titles when writing XML
  `<title>` elements to preserve intentional capitalization (`<fixed-case>` tags).

- Author names on a paper are `NameSpecification` objects wrapping a `Name`;
  they resolve to a canonical `Person` via `PersonIndex`. aclpub2-format input
  uses `first_name`/`last_name` keys, but the library's own `Name` uses
  `first`/`last`.

### Testing and verification scopes

**Before committing**, run `uv run pre-commit install` once so hooks
(ruff-check, ruff-format, XML schema validation via `jing`, JSON well-formedness,
trailing-whitespace/EOF-newline, license header insertion) run automatically.

Choose the appropriate testing scope based on what you changed:

- **`just check` (Default / Quick)**: Runs script unit tests, XML tab check, and
  all pre-commit hooks (~40s). Run this after any metadata changes under `data/`
  or scripts under `bin/`.
- **`just python test-all` (Library Unit Tests)**: Runs all non-integration
  pytest tests in `python/tests/` (~10s) using fake test data.
- **Targeted Integration Tests**: Run specific integration tests when verifying
  against real Anthology data without running the full suite:
  ```bash
  uv run pytest python/tests/anthology_integration_test.py -k "people"
  ```
- **`just python test-integration` (Full Integration Tests)**: Roundtrips every
  single XML collection and data file in the repository (~7-8 minutes, 3,400+
  tests). This runs in CI and is only needed locally when altering core library
  parsing/serialization logic.

## Content vs. presentation

Strict separation: **content** changes (paper metadata, SIGs, venues, etc.)
belong in `data/` (via the library) or the scripts that produce derived data;
**presentation** changes belong in Hugo templates/CSS.

- `bin/create_hugo_data.py` converts `data/` into the JSON Hugo consumes
  (`make hugo_data`); `bin/create_extra_bib.py` builds consolidated
  BibTeX/MODS/Endnote exports (`make bib`, skippable via `NOBIB=true`).
- Hugo templates live in `hugo/layouts/` (`_default/baseof.html` is the base
  skeleton; most pages are `**/single.html`; `papers/list-entry.html` renders
  paper entries in lists). CSS is Bootstrap 5.3, compiled from
  `hugo/assets/css/main.scss`.
- **The site has one theme** — don't invent a per-page sub-theme. Reuse existing
  SCSS tokens from `_colors.scss` (`$acl-black`, `$acl-muted`, `$acl-line`,
  `$acl-logo-red`, `$acl-soft-*`, exposed as `--acl-ink`/`--acl-muted`/
  `--acl-line` custom properties) and Bootstrap variables already in scope
  (`$blue`, `$border-width`, `$font-weight-*`, `media-breakpoint-*`, etc.).
  Never redeclare a shared value under a page-local name (e.g.
  `$acl-people-ink: #202124` duplicating `$acl-black`) or hardcode a hex that
  already exists in the palette — add genuinely new shared values to
  `_colors.scss` with a comment instead. Page-scoped custom properties are fine
  only when a value has no site-wide analogue. After changing SCSS, build the
  preview segment and diff `build/website/css/main.min.*.css` against the
  previous build; a pure refactor should produce no changed declarations, only
  renamed tokens.

## Scripts in `bin/`

General rule: scripts should use the `acl_anthology` library, run via
`uv run bin/<script>.py` (dependencies auto-resolved by uv; add new ones with
`uv add <pkg>` from the repo root, not by hand-editing `pyproject.toml`).
Notable ones (useful as reference implementations):

- `bin/ingest.py` — ingests new proceedings into the Anthology.
- `bin/create_hugo_data.py` — builds the website's Hugo data.
- `bin/generate_crossref_doi_metadata.py`, `bin/add_dois.py` — add DOIs.
- `bin/add_revision.py` — adds revisions from structured input.
- One-time transition scripts belong under `bin/oneoff/`.
