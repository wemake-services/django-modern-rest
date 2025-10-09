SHELL:=/usr/bin/env bash

.PHONY: lint
lint:
	poetry run ruff check --exit-non-zero-on-fix
	poetry run ruff format --check --diff
	poetry run flake8 .
	poetry run mypy .

.PHONY: unit
unit:
	# poetry run pytest

.PHONY: package
package:
	poetry run pip check

.PHONY: test
test: lint package unit
