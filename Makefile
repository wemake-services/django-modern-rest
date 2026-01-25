SHELL := /usr/bin/env bash

.PHONY: format
format:
	ruff format && ruff check && ruff format

.PHONY: lint
lint:
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .
	poetry run slotscheck --no-strict-imports -v -m django_modern_rest
	poetry run lint-imports

.PHONY: type-check
type-check:
	poetry run mypy .
	poetry run pyright
	poetry run pyrefly check

.PHONY: spell-check
spell-check:
	poetry run codespell django_modern_rest tests docs typesafety README.md CONTRIBUTING.md CHANGELOG.md

.PHONY: unit
unit:
	poetry run pytest --inline-snapshot=disable

.PHONY: smoke
smoke:
# Checks that it is possible to import the base package without django.setup
	poetry run python -c 'from django_modern_rest import Controller'

.PHONY: example
example:
	cd django_test_app && poetry run mypy --config-file mypy.ini
	PYTHONPATH='docs/' poetry run pytest -o addopts='' \
	  --suppress-no-test-exit-code \
	  docs/examples/testing/polyfactory_usage.py

.PHONY: package
package:
	poetry run pip check

.PHONY: test
test: lint type-check example spell-check package smoke unit
