# acl-anthology-py

[![License](https://img.shields.io/github/license/mbollmann/acl-anthology-py)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/mbollmann/acl-anthology-py/code-quality.yml)](https://github.com/mbollmann/acl-anthology-py/actions/workflows/code-quality.yml)
[![Code Coverage](https://img.shields.io/codecov/c/gh/mbollmann/acl-anthology-py)](https://codecov.io/gh/mbollmann/acl-anthology-py)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/acl-anthology-py)
![Development Status](https://img.shields.io/pypi/status/acl-anthology-py)
[![Package on PyPI](https://img.shields.io/pypi/v/acl-anthology-py)](https://pypi.org/project/acl-anthology-py/)

This package accesses data from the [ACL
Anthology](https://github.com/acl-org/acl-anthology).

API documentation can already be generated locally (see below for instructions),
more documentation (included a web-hosted version) is coming.

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

Some usage examples:

```python
paper = anthology.get("C92-1025")

print(str(paper.title))
# Two-Level Morphology with Composition

print([author.name for author in paper.authors])
# [Name(first='Lauri', last='Karttunen'), Name(first='Ronald M.', last='Kaplan'), Name(first='Annie', last='Zaenen')]

from acl_anthology.people import Name
print(anthology.people.get_by_name(Name("Lauri", "Karttunen")))
# [Person(id='lauri-karttunen', names=[Name(first='Lauri', last='Karttunen')],
#         item_ids={('C94', '2', '206'), ('W05', '12', '6'), ('C69', '70', '1'),
#                   ('J83', '2', '5'), ('C86', '1', '16'), ('C92', '1', '25'), ...})]
```

## Developing

This package uses **Python 3.10+** with the
[**Poetry**](https://python-poetry.org/) packaging system.

Cloning the repository and running `make` will install all dependencies via
Poetry, run all style and type checks, run all tests, and generate the
documentation.

### Install dependencies and pre-commit hooks

`make setup` will install all package dependencies in development mode, as well
as install the pre-commit hooks that run on every attempted git commit.

If you only want the dependencies, but not the hooks, run `make dependencies`.

### Running checks

`make check` will run [black](https://github.com/psf/black),
[ruff](https://github.com/charliermarsh/ruff), and [some other pre-commit
hooks](.pre-commit-config.yaml), as well as the
[mypy](https://mypy.readthedocs.io/) type checker on all files in the repo.

### Running tests

`make test` will run Python unit tests and integration tests.

### Running benchmarks

The [`benchmarks/`](benchmarks/) folder collects some benchmarks intended to be
run with the [richbench](https://github.com/tonybaloney/rich-bench) tool:

```bash
poetry run richbench benchmarks/
```

### Generating and writing documentation

- `make docs` (to generate in `site/`)
- `make docs-serve` (to serve locally)

Docstrings are written in [Google
style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings)
as this [supports the most
features](https://mkdocstrings.github.io/griffe/docstrings/#parsers-features)
with the mkdocstrings handler (particularly compared to Sphinx/reST).
