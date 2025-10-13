SHELL:=/usr/bin/env bash

.PHONY: format
format:
	ruff format && ruff check && ruff format

.PHONY: lint
lint:
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .

.PHONY: type-check
type-check:
	poetry run mypy .
	pyright

.PHONY: unit
unit:
	poetry run pytest

.PHONY: package
package:
	poetry run pip check

.PHONY: test
test: lint type-check package unit
