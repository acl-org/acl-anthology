# AGENTS.md

This file provides guidance to AI coding agents working in this directory. `CLAUDE.md` is a symlink to this file, so every harness reads the same instructions.

## Repository overview

This repository contains the authoritative data and code for the ACL Anthology,
a library of scientific publications.  This repo includes:

1. **Authoritative metadata** in `data/`: XML paper/volume metadata
   (`data/xml/*.xml`, one file per "collection", e.g. a conference/year) and
   JSON indices for people, venues, and SIGs (`data/json/`).
2. **Python library** in `python/`: the `acl_anthology` Python library
   (published to PyPI) that parses, models, and writes those data files. This is
   a separate `uv` workspace member with its own `pyproject.toml`, tests, and
   justfile.
3. **Static website templates/assets** in `hugo/`: the templates/assets used to
   render https://aclanthology.org/ from the data above via the Hugo static site
   generator (https://gohugo.io/).
4. **Scripts** in `bin/`: these include build scripts used during website
   generation, scripts invoked by Github action workflows, and scripts used
   manually by maintainers of the library (e.g. ingestion, fixups, report
   generation).

The Python workspace is managed by `uv`.  Root-level `pyproject.toml` and
`uv.lock` contain dependencies needed by scripts in `bin/`, and define a
workspace containing `python/` as a member; the root project depends on the
`acl-anthology` package from that workspace.

## Content changes always go through the library

For modifications or bugfixes concerning the authoritative `data/` directory,
**never parse `data/xml/*.xml` or `data/json/*.json` directly** — always use the
`acl_anthology` Python library (`python/`), whether writing a one-off `bin/`
script or fixing a bug. Only use its **public API** (nothing starting with `_`).

Read docstrings and `python/docs/` (or https://acl-anthology.readthedocs.io/)
before writing code against the library if unfamiliar with it.

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

## Common commands

Root level (site generation, whole-repo checks):

```bash
make site                # build the full Hugo website into build/anthology
make serve               # serve build/website/ at http://localhost:8000
make check               # test-scripts + XML tab check + pre-commit --all-files
just serve               # build (static+hugo_data+bib) and run `hugo server`
uv run bin/ingest.py -h  # run any bin/ script (uv resolves deps automatically)
```

Python library, from `python/` (or `just python <recipe>` from repo root):

```bash
just check                    # pre-commit (ruff + mypy + misc hooks) on all files
just test-all                 # pytest, excluding integration tests
just test NAME                # run only tests with NAME in the function name
just test-integration         # slow tests that load/save the real data/ tree
just typecheck                # mypy acl_anthology
just fix                      # run pre-commit twice (so autofixes get re-checked)
just fix-and-test             # fix + test-all
just repl                     # Python REPL with `anthology` pre-instantiated
just docs-serve               # serve mkdocs documentation locally
```

Equivalently with plain `uv`/`pytest` from `python/`:
`uv run pytest -m "not integration"`, `uv run pytest -k _NAME`, `uv run mypy acl_anthology`.

**Before committing**, run `uv run pre-commit install` once so hooks
(ruff-check, ruff-format, XML schema validation via `jing`, JSON well-formedness,
trailing-whitespace/EOF-newline, license header insertion) run automatically.
Integration tests are *not* part of pre-commit (too slow) but run in CI — run
them yourself (`just test-integration`) after modifying files under `data/`.

## Architecture of `acl_anthology` (`python/acl_anthology/`)

- **`Anthology`** (`anthology.py`) is the entry point. `Anthology.from_repo()`
  clones/pulls the repo into a cache dir; `Anthology.from_within_repo()` (the one
  to use for scripts living in this checkout) discovers the repo root via git and
  points at its `data/`. It exposes top-level indices: `.collections`, `.events`,
  `.people`, `.sigs`, `.venues`, plus convenience accessors (`get`,
  `get_volume`, `get_paper`, `find_people`, iterators `volumes()`/`papers()`) and
  `load_all()` / `save_all()`.
- **Containment hierarchy**, each level a lazy-loading `SlottedDict[T]`
  (`containers.py`): `CollectionIndex` → `Collection` (dict of `Volume`) →
  `Volume` (dict of `Paper`) → `Paper` (plain object, holds `parent` back-ref).
  IDs like `full_id`/`volume_id` are derived by walking `parent` chains rather
  than stored redundantly. `Collection.load()` streams the whole XML file with
  `lxml.etree.iterparse` in one pass — this stateful parsing (tracking the
  current volume as it goes) is why ad-hoc XML parsing elsewhere is unsafe.
- **People** (`people/`): `Name` is a normalized name; `NameSpecification` is a
  name *as written on a specific paper*, optionally carrying an `id` linking to
  a canonical `Person` in `PersonIndex`. `AnthologyID` (`utils/ids.py`) is
  `str | AnthologyIDTuple` where the tuple form is `(collection, volume, paper)`;
  `parse_id()`/`build_id()` convert to/from the string form (`"2025.acl-main.1"`).
- **Persistence**: paper/volume/event data round-trips through
  `data/xml/<collection-id>.xml` via `from_xml`/`to_xml` on each model class;
  saving uses a minimal-diff writer to avoid noisy formatting-only changes.
  People/venues/SIGs live in `data/json/{people,venues,sigs}.json`, loaded/saved
  with `msgspec.json`. `save_all()` only writes what's actually modified/loaded.
- XML must conform to `data/xml/schema.rnc` (RELAX NG compact); a bundled copy
  ships in `acl_anthology/data/` for a startup compatibility check.
- Tests (`python/tests/`) mirror the package layout. `conftest.py` provides an
  `anthology` fixture built from a **self-contained fake data tree**
  (`python/tests/data/anthology/`) via `pytest-datadir` — based on real
  proceedings but with deliberately fabricated data; never overwrite it from the
  real `data/`. There's also a lightweight `anthology_stub` mock fixture for
  tests that don't need a full `Anthology`.
- Docstrings may not use line-wrapping; all line breaks are rendered as hard
  line breaks by Mkdocs.
- Functional changes to the library should be accompanied by a corresponding
  statement in `CHANGELOG.md`; keep this very concise unless there are major
  changes.

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
- When adding a new year, update `$all_years` (and `$border_years` if needed)
  and the `colspan` table headers in `hugo/layouts/index.html`.

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

## Watermark tool

`hugo/static/cgi-bin/watermark.cgi` + `add_footer_to_pdf.py` implement a CGI
service (linked from `bin/add_footer_to_pdf.py` for CLI use) that adds an
ACL-style footer/page numbers to a PDF; `hugo/static/js/watermark.js` +
`hugo/content/watermark.md` render its client UI. It enforces a 25 MB upload
limit, bounded multipart parsing, numeric-option validation, and a 2,000-char/
8-line footer limit with only balanced `<i>` tags allowed. A plain
`python -m http.server` can display the page but not process submissions
(needs a CGI-capable server); each request uses a temp dir removed on
success/error.
