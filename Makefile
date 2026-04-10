SHELL := /usr/bin/env bash

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: format
format: ## Format code with ruff
	uv run ruff format && uv run ruff check && uv run ruff format

.PHONY: lint
lint: ## Run linting checks
	uv run ruff check --exit-non-zero-on-fix
	uv run ruff format --check --diff
	uv run flake8 .
	uv run slotscheck -v -m dmr
	uv run lint-imports

.PHONY: type-check
type-check: ## Run all type checkers we support
	uv run mypy .
	uv run pyright
	uv run pyrefly check

.PHONY: translations
translations: ## Run translation QA
	uv run dennis-cmd lint dmr/locale
	uv run django-admin compilemessages --ignore dmr || true
	uv run django-admin compilemessages

.PHONY: unit
unit: ## Run unit tests with pytest
	uv run pytest --inline-snapshot=disable

.PHONY: smoke
smoke: ## Run smoke tests (check that package can be imported without `django.setup`)
	uv run python -c 'from dmr import Controller'
	# Checks that renderers and parsers can be imported
	# from settings without `.setup()` call:
	uv run python -c 'from dmr.renderers import *'
	uv run python -c 'from dmr.parsers import *'
	# Checks that auth can be imported from settings without `.setup()` call:
	uv run python -c 'from dmr.security import *'
	uv run python -c 'from dmr.security.django_session import *'
	uv run python -c 'from dmr.security.jwt import *'
	uv run python -c 'from dmr.openapi.config import *'
	uv run python -c 'from dmr.openapi.objects import *'
	# Settings itself can be imported with `.setup()`:
	uv run python -c 'from dmr import settings'

.PHONY: example
example: ## Run QA tools on example code
	( cd django_test_app \
		&& uv run mypy --config-file mypy.ini \
		&& uv run python manage.py makemigrations --dry-run --check \
		)
	PYTHONPATH='docs/' uv run pytest -o addopts='' \
	  --suppress-no-test-exit-code \
	  docs/examples/testing/polyfactory_usage.py \
	  docs/examples/testing/django_builtin_client.py \
	  docs/examples/testing/dmr_helpers.py

.PHONY: example-run
example-run: ## Run example app
	cd django_test_app && uv run python manage.py runserver

.PHONY: package
package: ## Check package dependencies
	# TODO: remove `|| true` once we can support `orjson` in `pyproject.toml`
	uv sync --all-groups --all-extras --locked --check || true
	uv pip check
	uv --preview-features audit audit

.PHONY: benchmarks-type-check
benchmarks-type-check: ## Run type check on benches
	cd benchmarks && uv run mypy tests/

.PHONY: benchmarks
benchmarks: mypyc ## Run feature benches
	uv run pytest benchmarks/tests -o 'addopts="--codspeed"'

.PHONY: mypyc
mypyc: clean ## Compile code with mypyc
	HATCH_BUILD_HOOKS_ENABLE=1 uv build --wheel

.PHONY: clean
clean: ## Clean all build files
	rm -rf build/ dist/
	find dmr/_compiled -type f -name '*.so' | xargs rm -rf

.PHONY: test
test: lint type-check example benchmarks-type-check package smoke translations unit ## Run all checks
