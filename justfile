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
    uv run ruff format
    uv run ruff check

# Run all linters
[group('dev')]
lint:
    uv run ruff check --exit-non-zero-on-fix
    uv run ruff format --check --diff
    uv run flake8 .
    uv run slotscheck -v -m dmr
    uv run lint-imports

# Run all checks
[group('dev')]
test: lint type-check example benchmarks-type-check package smoke translations unit

# Run all type checkers
[group('type-check')]
type-check:
    uv run mypy .
    uv run pyright
    uv run pyrefly check --remove-unused-ignores

# Run unit tests
[group('testing')]
unit:
    uv run pytest --inline-snapshot=disable

# Check package imports without django.setup()
[group('testing')]
smoke:
    uv run python -c 'from dmr import Controller'
    # Checks that renderers and parsers can be imported
    # from settings without `.setup()` call:
    uv run python -c 'from dmr.renderers import *'
    uv run python -c 'from dmr.parsers import *'
    # Checks that auth can be imported from settings without `.setup()` call:
    uv run python -c 'from dmr.security import *'
    uv run python -c 'from dmr.security.django_session import *'
    uv run python -c 'from dmr.security.jwt import *'
    uv run python -c 'from dmr.throttling import *'
    uv run python -c 'from dmr.throttling.backends import *'
    uv run python -c 'from dmr.throttling.algorithms import *'
    uv run python -c 'from dmr.throttling.cache_keys import *'
    uv run python -c 'from dmr.openapi.config import *'
    uv run python -c 'from dmr.openapi.objects import *'
    # Settings itself can be imported with `.setup()`:
    uv run python -c 'from dmr import settings'

# Run QA tools on example code
[group('testing')]
example:
    cd django_test_app \
      && uv run mypy --config-file mypy.ini \
      && uv run python manage.py makemigrations --dry-run --check \
      && uv run python manage.py collectstatic --no-input --dry-run
    PYTHONPATH='docs/' uv run pytest -o addopts='' \
      --suppress-no-test-exit-code \
      docs/examples/testing/polyfactory_usage.py \
      docs/examples/testing/django_builtin_client.py \
      docs/examples/testing/dmr_helpers.py

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
    cd benchmarks && uv run mypy tests/

# Compile with mypyc then run feature benchmarks
[group('benchmarks')]
benchmarks: mypyc
    uv run pytest benchmarks/tests -o 'addopts="--codspeed"'

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
