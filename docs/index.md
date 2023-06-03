# ACL Anthology Python Library

This is a Python package for accessing data from the [ACL
Anthology](https://github.com/acl-org/acl-anthology).

!!! danger

    **This library is WORK IN PROGRESS and not yet functional.**

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

### Running benchmarks

```bash
poetry run richbench benchmarks/
```

### Project layout

    acl_anthology/   # Main package directory.
    benchmarks/      # Benchmark scripts.
    docs/            # The mkdocs documentation.
    tests/           # Pytest tests.
