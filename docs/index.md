# Overview

This is a Python library for accessing data from the [ACL
Anthology](https://github.com/acl-org/acl-anthology).

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

To install the package and its dependencies in development mode, clone the
repository and run `poetry install`.

### Running checks and pre-commit hooks

To run [black](https://github.com/psf/black),
[ruff](https://github.com/charliermarsh/ruff), and some other pre-commit hooks
on all files in the repo:

```bash
poetry run pre-commit run --all-files
```

To install pre-commit hooks so they run on every attempted commit:

```bash
poetry run pre-commit install
```

### Running tests

```bash
poetry run pytest
```

### Running typechecks

```bash
poetry run mypy acl_anthology
```

### Running benchmarks

```bash
poetry run richbench benchmarks/
```

### Project layout

    acl_anthology/   # Main package directory.
    benchmarks/      # Benchmark scripts.
    docs/            # The mkdocs documentation.
    tests/           # Pytest tests.
