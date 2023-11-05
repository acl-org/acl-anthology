# acl-anthology-py

[![License](https://img.shields.io/github/license/acl-org/acl-anthology)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/acl-org/acl-anthology/code-quality.yml)](https://github.com/acl-org/acl-anthology/actions/workflows/code-quality.yml)
[![Documentation](https://img.shields.io/readthedocs/acl-anthology-py)](https://acl-anthology-py.readthedocs.io/en/latest/)
[![Code Coverage](https://img.shields.io/codecov/c/gh/acl-org/acl-anthology)](https://codecov.io/gh/acl-org/acl-anthology)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/acl-anthology-py)
![Development Status](https://img.shields.io/pypi/status/acl-anthology-py)
[![Package on PyPI](https://img.shields.io/pypi/v/acl-anthology-py)](https://pypi.org/project/acl-anthology-py/)

This package accesses data from the [ACL
Anthology](https://aclanthology.org).

- [**Documentation**](https://acl-anthology-py.readthedocs.io/en/latest/)
- [**Package on PyPI**](https://pypi.org/project/acl-anthology-py/)

## How to use

Install via `pip`:

```bash
$ pip install acl-anthology-py
```

Instantiate the library, automatically fetching data files from the [ACL
Anthology repo](https://github.com/acl-org/acl-anthology) (requires `git` to be
installed on your system):

```python
from acl_anthology import Anthology
anthology = Anthology.from_repo()
```

Some brief usage examples:

```pycon
>>> paper = anthology.get("C92-1025")
>>> str(paper.title)
Two-Level Morphology with Composition
>>> [author.name for author in paper.authors]
[
    Name(first='Lauri', last='Karttunen'),
    Name(first='Ronald M.', last='Kaplan'),
    Name(first='Annie', last='Zaenen')
]
>>> anthology.find_people("Karttunen, Lauri")
[
    Person(
        id='lauri-karttunen', names=[Name(first='Lauri', last='Karttunen')],
        item_ids=<set of 30 AnthologyIDTuple objects>, comment=None
    )
]
```

Find more examples and details on the API in the [**official
documentation**](https://acl-anthology-py.readthedocs.io/en/latest/).

## Developing

This package uses the [**Poetry**](https://python-poetry.org/) packaging system.
Development is easiest with the [**just**](https://github.com/casey/just)
command runner; running `just -l` will list all available recipes, while `just
-n <recipe>` will print the commands that the recipe would run.

### Running checks, pre-commit hooks, and tests

- `just check` will run [**black**](https://github.com/psf/black),
   [**ruff**](https://github.com/charliermarsh/ruff),
   [**mypy**](https://mypy.readthedocs.io), and some other pre-commit hooks on all
   files in the repo.

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

### Running benchmarks

There are some benchmark scripts intended to be run with
[richbench](https://github.com/tonybaloney/rich-bench):

```bash
poetry run richbench benchmarks/
```

### Generating and writing documentation

- `just docs` generates the documentation in the `site/` folder.
- `just docs-serve` serves the documentation for local browsing.

Docstrings are written in [Google
style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings)
as this [supports the most
features](https://mkdocstrings.github.io/griffe/docstrings/#parsers-features)
with the mkdocstrings handler (particularly compared to Sphinx/reST).
