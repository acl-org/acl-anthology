run := poetry run

### Most common targets for developing

.PHONY: all
all: check test docs

.PHONY: check
check: pre-commit typecheck

.PHONY: test
test: pytest

### Package setup

.PHONY: dependencies
dependencies: .flag_installed

.flag_installed:
	poetry install --with dev
	@touch .flag_installed

.git/hooks/pre-commit: .flag_installed .pre-commit-config.yaml
	poetry run pre-commit install

.PHONY: setup
setup: .flag_installed .git/hooks/pre-commit

### Check, test, build commands

.PHONY: pytest
pytest: .flag_installed
	$(run) pytest --cov=acl_anthology --cov-report=xml

.PHONY: typecheck
typecheck: .flag_installed
	$(run) mypy acl_anthology

.PHONY: pre-commit
pre-commit: .flag_installed
	$(run) pre-commit run --all-files

.PHONY: autofix
autofix: .flag_installed
	$(run) black acl_anthology/ tests/
	$(run) ruff check --fix-only acl_anthology/ tests/

### Documentation

.PHONY: docs
docs: .flag_installed
	$(run) mkdocs build

.PHONY: docs-serve
docs-serve: .flag_installed
	$(run) mkdocs serve
