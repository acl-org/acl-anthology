# acl-anthology-py

[![License](https://img.shields.io/github/license/mbollmann/acl-anthology-py)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/mbollmann/acl-anthology-py/main.yml)](https://github.com/mbollmann/acl-anthology-py/actions/workflows/main.yml)
[![Code Coverage](https://img.shields.io/codecov/c/gh/mbollmann/acl-anthology-py)](https://codecov.io/gh/mbollmann/acl-anthology-py)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/acl-anthology-py)
![Development Status](https://img.shields.io/badge/status-pre--alpha-red)
<!--
[![Package on PyPI](https://img.shields.io/pypi/v/acl-anthology-py)](https://pypi.org/project/acl-anthology-py/)
 -->

This package accesses data from the [ACL
Anthology](https://github.com/acl-org/acl-anthology).

## About

:warning::warning::warning: **This repository is WORK IN PROGRESS and not yet
functional.** :warning::warning::warning:

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
