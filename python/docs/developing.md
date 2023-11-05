# For Developers

This package uses the [**Poetry**](https://python-poetry.org/) packaging system.
Development is easiest with the [**just**](https://github.com/casey/just)
command runner; running `just -l` will list all available recipes, while `just
-n <recipe>` will print the commands that the recipe would run.

## Running checks and tests

- `just check` will run [**black**](https://github.com/psf/black),
   [**ruff**](https://github.com/charliermarsh/ruff),
   [**mypy**](https://mypy.readthedocs.io), and [some other pre-commit
   hooks](https://github.com/acl-org/acl-anthology/blob/master/.pre-commit-config.yaml)
   on all files in the repo.

    - `just install-hooks` will install pre-commit hooks so they run on every
      attempted commit.

- `just test-all` will run all tests _except_ for tests that run on the full
  Anthology data.

    - `just test NAME` will only run test functions with `NAME` in them.
    - `just test-integration` will run tests on the full Anthology data.

- `just fix-and-test` (or `just ft` for short) will run all checks and tests,
  additionally re-running the checks on failure, so that the checking and
  testing will continue even if some hooks have modified files.

- The justfile defines several more useful recipes; list them with `just -l`!

## Running benchmarks

There are some benchmark scripts intended to be run with
[richbench](https://github.com/tonybaloney/rich-bench):

```bash
poetry run richbench benchmarks/
```

## Generating and writing documentation

- `just docs` generates the documentation in the `site/` folder.
- `just docs-serve` serves the documentation for local browsing.

Docstrings are written in [Google
style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings)
as this [supports the most
features](https://mkdocstrings.github.io/griffe/docstrings/#parsers-features)
with the mkdocstrings handler (particularly compared to Sphinx/reST).

## Project layout

    acl_anthology/   # Main package directory.
    benchmarks/      # Benchmark scripts.
    docs/            # The mkdocs documentation.
    tests/           # Pytest tests.
