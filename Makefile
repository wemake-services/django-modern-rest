SHELL := /usr/bin/env bash
# Override with, for example: POETRY='uvx poetry' make test
POETRY ?= poetry

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: format
format: ## Format code with ruff
	$(POETRY) run ruff format && $(POETRY) run ruff check && $(POETRY) run ruff format

.PHONY: lint
lint: ## Run linting checks
	$(POETRY) run ruff check --exit-non-zero-on-fix
	$(POETRY) run ruff format --check --diff
	$(POETRY) run flake8 .
	$(POETRY) run slotscheck --no-strict-imports -v -m dmr \
		--exclude-modules 'dmr\.security\.jwt\.blocklist|dmr\.security\.django_session\.views'
	$(POETRY) run lint-imports

.PHONY: type-check
type-check: ## Run all type checkers we support
	$(POETRY) run mypy .
	$(POETRY) run pyright
	$(POETRY) run pyrefly check

.PHONY: spell-check
spell-check: ## Run spell checking
	$(POETRY) run codespell dmr tests docs typesafety README.md CONTRIBUTING.md CHANGELOG.md

.PHONY: unit
unit: ## Run unit tests with pytest
	$(POETRY) run pytest --inline-snapshot=disable

.PHONY: smoke
smoke: ## Run smoke tests (check that package can be imported without `django.setup`)
	$(POETRY) run python -c 'from dmr import Controller'
	# Checks that renderers and parsers can be imported
	# from settings without `.setup()` call:
	$(POETRY) run python -c 'from dmr.renderers import *'
	$(POETRY) run python -c 'from dmr.parsers import *'
	# Checks that auth can be imported from settings without `.setup()` call:
	$(POETRY) run python -c 'from dmr.security import *'
	$(POETRY) run python -c 'from dmr.security.django_session import *'
	$(POETRY) run python -c 'from dmr.security.jwt import *'
	$(POETRY) run python -c 'from dmr.openapi.config import *'
	$(POETRY) run python -c 'from dmr.openapi.objects import *'
	# Settings itself can be imported with `.setup()`:
	$(POETRY) run python -c 'from dmr import settings'

.PHONY: example
example: ## Run mypy and pytest on example code
	cd django_test_app && $(POETRY) run mypy --config-file mypy.ini
	PYTHONPATH='docs/' $(POETRY) run pytest -o addopts='' \
	  --suppress-no-test-exit-code \
	  docs/examples/testing/polyfactory_usage.py \
	  docs/examples/testing/django_builtin_client.py \
	  docs/examples/testing/dmr_helpers.py

.PHONY: example-run
example-run: ## Run example app
	cd django_test_app && $(POETRY) run python manage.py runserver

.PHONY: package
package: ## Check package dependencies with pip
	$(POETRY) run pip check

.PHONY: test
test: lint type-check example spell-check package smoke unit ## Run all checks
