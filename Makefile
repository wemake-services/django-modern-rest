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
	ruff format && ruff check && ruff format

.PHONY: lint
lint: ## Run linting checks
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .
	poetry run slotscheck --no-strict-imports -v -m django_modern_rest
	poetry run lint-imports

.PHONY: type-check
type-check: ## Run all type checkers we support
	poetry run mypy .
	poetry run pyright
	poetry run pyrefly check

.PHONY: spell-check
spell-check: ## Run spell checking
	poetry run codespell django_modern_rest tests docs typesafety README.md CONTRIBUTING.md CHANGELOG.md

.PHONY: unit
unit: ## Run unit tests with pytest
	poetry run pytest --inline-snapshot=disable

.PHONY: smoke
smoke: ## Run smoke tests (check that package can be imported without `django.setup`)
	poetry run python -c 'from django_modern_rest import Controller'
	# Checks that auth can be imported from settings without `.setup()` call:
	poetry run python -c 'from django_modern_rest.security import *'
	poetry run python -c 'from django_modern_rest.security.jwt import *'

.PHONY: example
example: ## Run mypy and pytest on example code
	cd django_test_app && poetry run mypy --config-file mypy.ini
	PYTHONPATH='docs/' poetry run pytest -o addopts='' \
	  --suppress-no-test-exit-code \
	  docs/examples/testing/polyfactory_usage.py

.PHONY: run-example
run-example: ## Run example app
	cd django_test_app && poetry run python manage.py runserver

.PHONY: package
package: ## Check package dependencies with pip
	poetry run pip check

.PHONY: test
test: lint type-check example spell-check package smoke unit ## Run all checks
