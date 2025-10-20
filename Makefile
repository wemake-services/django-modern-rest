SHELL:=/usr/bin/env bash

.PHONY: format
format:
	ruff format && ruff check && ruff format

.PHONY: lint
lint:
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .
	poetry run slotscheck -v -m django_modern_rest
	poetry run lint-imports

.PHONY: type-check
type-check:
	poetry run mypy .
	poetry run pyright

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

.PHONY: package
package:
	poetry run pip check

.PHONY: test
test: lint type-check spell-check package smoke unit
