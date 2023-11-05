run := poetry run

### Most common targets for developing

.PHONY: all
all: check test docs

.PHONY: check
check: pre-commit typecheck

.PHONY: test
test: pytest

.PHONY: fix-and-test
fix-and-test: pre-commit-autofix typecheck pytest

### Package setup

.PHONY: dependencies
dependencies: .flag_installed
.flag_installed: pyproject.toml poetry.lock
	poetry install --with dev
	@touch .flag_installed

.PHONY: install-hooks
install-hooks: .git/hooks/pre-commit
.git/hooks/pre-commit: .flag_installed .pre-commit-config.yaml
	$(run) pre-commit install

.PHONY: clean
clean:
	@for folder in .mypy_cache/ .ruff_cache/ .pytest_cache/ dist/ site/; do \
	  if [[ -d "$$folder" ]]; then \
	    rm -rfv "$$folder" ; \
	  fi; \
	done
	@find . -type d -name __pycache__ -exec rm -rfv "{}" +
	@poetry run pre-commit uninstall
	@poetry env remove --all -n
	@rm -fv coverage.xml .flag_installed

### Check, test, build commands

.PHONY: test-integration
test-integration: .flag_installed
	$(run) pytest -m "integration" --cov=acl_anthology --cov-report=xml

.PHONY: pytest
pytest: .flag_installed
	$(run) pytest -m "not integration" --cov=acl_anthology --cov-report=xml

.PHONY: typecheck
typecheck: .flag_installed
	$(run) mypy acl_anthology

.PHONY: pre-commit
pre-commit: .flag_installed
	$(run) pre-commit run --all-files

# Runs pre-commit twice in case of failure, so that it will pass the second time
# if only auto-fixing hooks have triggered
.PHONY: pre-commit-autofix
pre-commit-autofix: .flag_installed
	@$(run) pre-commit run --all-files || $(run) pre-commit run --all-files

.PHONY: test-all-python-versions
test-all-python-versions:
	@for py in 3.10 3.11 3.12; do \
	  poetry env use $$py ; \
	  poetry install --with dev --quiet ; \
	  poetry run pytest -m "not integration" ; \
	done

#.PHONY: autofix
#autofix: .flag_installed
#	$(run) black acl_anthology/ tests/
#	$(run) ruff check --fix-only acl_anthology/ tests/

### Documentation

.PHONY: docs
docs: .flag_installed
	$(run) mkdocs build

.PHONY: docs-serve
docs-serve: .flag_installed
	$(run) mkdocs serve
