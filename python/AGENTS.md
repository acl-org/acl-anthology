# AGENTS.md

This directory contains the `acl-anthology` Python library (published to PyPI).

The Python environment is managed by `uv`. It is part of a larger workspace
defined in the parent directory.

## Commands

```bash
just check                # pre-commit (ruff + mypy + misc hooks) on all files
just fix                  # run pre-commit twice (so autofixes get re-checked)
just typecheck            # only run mypy
just test-all             # pytest, excluding integration tests
just test NAME            # run only tests with NAME in the function name
just test-integration     # slow tests that load/save the real ../data/ tree (expensive)
just docs                 # build mkdocs documentation locally
```

Equivalently with plain `uv`/`pytest`:
`uv run pytest -m "not integration"`, `uv run pytest -k _NAME`, `uv run mypy acl_anthology`.

## Coding style

- Consistent coding style is ensured by ruff and mypy, run via `just check`.
- Do not soft-wrap lines within docstrings; this breaks the rendering in the
  documentation as they are rendered as hard line breaks by Mkdocs.
- Functional changes should be accompanied by a corresponding entry in
  `CHANGELOG.md`; keep this very concise unless there are major changes.
- Functional changes should always be covered by tests in `tests/`.
  - The structure of `tests/` mirrors the package layout.
  - `conftest.py` provides an `anthology` fixture built from a **self-contained
    fake data tree** (`tests/data/anthology/`) via `pytest-datadir` — based on
    real proceedings but with deliberately fabricated data; never overwrite it
    from the real data.

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
- XML must conform to `../data/xml/schema.rnc` (RELAX NG compact); a bundled
  copy ships in `acl_anthology/data/` for a startup compatibility check.
