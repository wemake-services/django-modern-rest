set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set dotenv-load := false

# Do not update the env, when running
export UV_NO_SYNC := '1'

# List all available recipes
_default:
    @just --list --unsorted --list-submodules

# Benchmarks module
mod bench 'benchmarks/justfile'

# Docs module
mod _docs 'docs/justfile'

# Install dependencies
[group('dev')]
install:
    uv sync --all-groups --all-extras

# Format code with ruff
[group('dev')]
format:
    uv run python -m ruff format
    uv run python -m ruff check

# Run all linters
[group('dev')]
lint:
    uv run python -m ruff check --exit-non-zero-on-fix
    uv run python -m ruff format --check --diff
    uv run python -m flake8 .
    uv run python -m slotscheck -v -m dmr
    uv run import-linter lint

# Run all checks
[group('dev')]
test: lint type-check example benchmarks-type-check package \
  (smoke 'jwt' 'msgspec' 'pydantic') translations unit

# Run all type checkers
[group('type-check')]
type-check:
    uv run python -m mypy .
    uv run python -m pyright
    uv run python -m pyrefly check --remove-unused-ignores

# Run unit tests
[group('testing')]
unit *args='':
    uv run python -m pytest -n auto --max-worker-restart=1 \
      --inline-snapshot=disable {{ args }}

# Check package imports without django.setup(); extras are optional, e.g. `just smoke jwt msgspec`
[group('testing')]
smoke *extras='':
    uv run python -c 'from dmr import Controller'
    # Checks that renderers and parsers can be imported
    # from settings without `.setup()` call:
    uv run python -c 'from dmr.renderers import *'
    uv run python -c 'from dmr.parsers import *'
    # Checks that auth can be imported from settings without `.setup()` call:
    uv run python -c 'from dmr.security import *'
    uv run python -c 'from dmr.security.django_session import *'
    uv run python -c 'from dmr.security.token import *'
    uv run python -c 'from dmr.throttling import *'
    uv run python -c 'from dmr.throttling.backends import *'
    uv run python -c 'from dmr.throttling.algorithms import *'
    uv run python -c 'from dmr.throttling.cache_keys import *'
    uv run python -c 'from dmr.openapi.config import *'
    uv run python -c 'from dmr.openapi.objects import *'
    # Settings itself can be imported with `.setup()`:
    uv run python -c 'from dmr import settings'
    # Requires extras:
    for extra in {{ extras }}; do \
      case "$extra" in \
        jwt) uv run python -c 'from dmr.security.jwt import *' ;; \
        msgspec) uv run python -c 'from dmr.plugins.msgspec import *' ;; \
        pydantic) uv run python -c 'from dmr.plugins.pydantic import *' ;; \
      esac; \
    done

# Run QA tools on example code
[group('testing')]
example:
    cd django_test_app \
      && uv run python -m mypy --config-file mypy.ini \
      && uv run python manage.py makemigrations --dry-run --check \
      && uv run python manage.py collectstatic --no-input --dry-run
    PYTHONPATH='docs/' uv run python -m pytest -o addopts='' \
      docs/examples/testing/polyfactory_usage.py \
      docs/examples/testing/django_builtin_client.py \
      docs/examples/testing/dmr_helpers.py \
      docs/examples/testing/pytest_plugin.py \
      docs/examples/testing/throttling_unittest.py \
      docs/examples/testing/throttling_pytest.py \
      docs/examples/testing/test_view_with_auth.py \
      docs/examples/testing/test_view_disabled_auth.py

# Start Django + DRM example app
[group('testing')]
example-run:
    cd django_test_app && uv run python manage.py runserver

# Validate package dependencies and run security audit
[group('testing')]
package:
    # TODO: remove `-` once we can support `orjson` in `pyproject.toml`
    -uv sync --all-groups --all-extras --locked --check
    uv pip check
    uv --preview-features audit audit

# Type-check benchmark code
[group('benchmarks')]
benchmarks-type-check:
    cd benchmarks && uv run python -m mypy tests/

# Compile with mypyc then run feature benchmarks
[group('benchmarks')]
benchmarks: mypyc
    uv run python -m pytest benchmarks/tests -o 'addopts="--codspeed"'

# Compile code with mypyc
[group('build')]
mypyc: clean
    HATCH_BUILD_HOOKS_ENABLE=1 uv build --wheel

# Remove build artifacts and compiled .so files
[group('build')]
clean:
    rm -rf build/ dist/
    find dmr/_compiled -type f -name '*.so' | xargs rm -rf

# Build docs
[group('docs')]
docs +targets='clean html': (_docs::build targets)

# Add new translation strings
[group('i18n')]
makemessages:
  #!/usr/bin/env bash
  for target in $(find dmr/locale -mindepth 1 -maxdepth 1 -type d); do
    uv run django-admin makemessages -l "$(basename "$target")" \
      --add-location never
  done

# Run translation QA
[group('i18n')]
translations:
    uv run dennis-cmd lint dmr/locale
    uv run django-admin compilemessages --ignore dmr || true
    uv run django-admin compilemessages
