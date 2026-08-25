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

## Website styling (`hugo/assets/css/`)

The site has **one theme**. Do not invent a per-page sub-theme when adding a new
page or component — that is how designs drift apart and how a site-wide restyle
becomes impossible.

- **Reuse existing tokens.** Colors live in `_colors.scss` (`$acl-black`,
  `$acl-muted`, `$acl-line`, `$acl-logo-red`, `$acl-soft-*`) and are exposed as
  `--acl-ink`, `--acl-muted`, `--acl-line` on `:root` in `main.scss`. Bootstrap
  variables (`$blue`, `$cyan`, `$white`, `$border-width`, `$font-weight-*`,
  `$zindex-*`, `media-breakpoint-*`) are also in scope.
- **Never declare a page-local copy of a shared value.** `$acl-people-ink: #202124`
  next to an existing `$acl-black: #202124` is the exact anti-pattern; a hard-coded
  hex that already exists in the palette is the same mistake.
- **If you genuinely need a new shared value, add it to `_colors.scss`** with a
  one-line comment on what it is for, then use it everywhere it applies.
- Page-scoped custom properties (e.g. `--acl-home-paper`) are fine only when the
  value really is specific to that page and has no site-wide analogue.
- Prefer existing Bootstrap utilities and components over bespoke CSS.
- After changing SCSS, verify the compiled output: build the preview segment and
  diff `build/website/css/main.min.*.css` against the previous build. A pure
  refactor should produce no changed declarations, only renamed tokens.

## Important scripts in `bin/`

These may be useful as references for how the library works.

- `bin/ingest.py` — Ingests new proceedings into the Anthology.
- `bin/create_hugo_data.py` — Builds the website data.
- `bin/generate_crossref_doi_metadata.py` and `bin/add_dois.py` — Add DOIs to ingested volumes.
- `bin/add_revision.py` — Adds revisions by reading from structured input.

One-time transition scripts go under `bin/oneoff/`.
