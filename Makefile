SHELL:=/usr/bin/env bash

.PHONY: format
format:
	ruff format && ruff check && ruff format

.PHONY: lint
lint:
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .
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

.PHONY: package
package:
	poetry run pip check

.PHONY: test
test: lint type-check spell-check package unit
