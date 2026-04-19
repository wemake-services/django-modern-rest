import os
import sys
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from types import BuiltinFunctionType, FunctionType, ModuleType
from typing import TypeAlias

import pytest

_CleanModules: TypeAlias = Callable[
    [set[str]],
    AbstractContextManager[dict[str, ModuleType]],
]


@pytest.fixture
def clean_modules() -> _CleanModules:
    """Fixture to clean required modules."""

    @contextmanager
    def factory(names: set[str]) -> Iterator[dict[str, ModuleType]]:
        orig_modules = {}
        prefixes = tuple(f'{name}.' for name in names)
        for modname in list(sys.modules):
            if modname in names or modname.startswith(prefixes):
                orig_modules[modname] = sys.modules.pop(modname)

        yield orig_modules

        sys.modules.update(orig_modules)

    return factory


@pytest.mark.parametrize(
    ('accept', 'provided_types', 'best_match'),
    [
        ('text/plain', ['text/plain'], 'text/plain'),
        ('text/plain', ['text/html'], None),
        ('text/*', ['text/html'], 'text/html'),
        ('*/*', ['text/html'], 'text/html'),
        ('', ['text/html'], None),
        ('text/plain;p=test', ['text/plain'], 'text/plain'),
        ('text/plain', ['text/plain;p=test'], None),
        ('text/plain;p=test', ['text/plain;p=test'], 'text/plain;p=test'),
        ('text/plain', ['text/*'], 'text/plain'),
        ('text/html', ['*/*'], 'text/html'),
        (
            'text/plain;q=0.8,text/html',
            ['text/plain', 'text/html'],
            'text/html',
        ),
        (
            'text/plain;q=ab,text/html',
            ['text/plain', 'text/html'],
            'text/plain',
        ),
        (
            'text/*;q=0.3, text/html;q=0.7, text/html;level=1, */*;q=0.5',
            ['text/plain', 'text/html'],
            'text/html',
        ),
        ('text/*,text/html', ['text/plain', 'text/html'], 'text/html'),
        ('text/*,text/html', ['application/json', 'application/xml'], None),
        ('', [], None),
        ('text/plain,', [], None),
        ('', ['text/plain'], None),
        ('application/json', ['text/plain', 'text/html'], None),
    ],
)
@pytest.mark.parametrize('compiled', [True, False])
def test_accept_best_match(
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: _CleanModules,
    *,
    accept: str,
    provided_types: list[str],
    best_match: str | None,
    compiled: bool,
) -> None:
    """Ensure that selection of accepted type works correctly."""
    # Our setup, it can be compiled or not:
    monkeypatch.setenv('DMR_USE_COMPILED', str(int(compiled)))
    with clean_modules({'dmr.envs', 'dmr.compiled'}):
        from dmr.compiled import accepted_type  # noqa: PLC0415
        from dmr.envs import USE_COMPILED  # noqa: PLC0415

        assert USE_COMPILED is compiled
        if compiled:
            assert '_pure' not in accepted_type.__module__, (
                USE_COMPILED,
                compiled,
            )
        else:
            assert '_pure' in accepted_type.__module__, (USE_COMPILED, compiled)
            assert isinstance(accepted_type, FunctionType)

        # The function itself:
        assert accepted_type(accept, provided_types) == best_match


def test_accept_correct_import() -> None:
    """Ensure that the default import is correct."""
    from dmr.compiled import accepted_type  # noqa: PLC0415
    from dmr.envs import USE_COMPILED  # noqa: PLC0415

    if USE_COMPILED:  # pragma: no cover
        assert '_pure' not in accepted_type.__module__, USE_COMPILED
    else:  # pragma: no cover
        assert '_pure' in accepted_type.__module__, USE_COMPILED
        assert isinstance(accepted_type, FunctionType)

    with pytest.raises((AttributeError, TypeError), match='int'):
        accepted_type(1, 2)  # type: ignore[arg-type]


def test_accept_correct_type() -> None:  # pragma: no cover
    """Ensure that the default import is correct."""
    from dmr.compiled import accepted_type  # noqa: PLC0415

    enabled = os.environ.get('HATCH_BUILD_HOOKS_ENABLE')
    if enabled is None:
        pytest.skip(reason='This test only runs in cibuildwheel')
    assert isinstance(accepted_type, BuiltinFunctionType), enabled


@pytest.mark.parametrize(
    ('accept_value', 'media_type', 'request_accepts_type_by_header'),
    [
        ('text/plain', 'text/plain', True),
        ('text/plain', 'text/html', False),
        ('text/*', 'text/html', True),
        ('*/*', 'text/html', True),
        ('text/plain;p=test', 'text/plain;p=test', True),
        (
            'text/*;q=0.3, text/html;q=0.7, text/html;level=1, */*;q=0.5',
            'text/plain',
            True,
        ),
        ('text/plain', 'text/*', True),
        ('text/html', '*/*', True),
        ('text/plain;q=0.8,text/html', 'text/plain', True),
        ('text/plain;q=0.8,text/html', 'text/html', True),
        ('text/plain;q=ab,text/html', 'text/plain', True),
        ('text/plain;q=ab,text/html', 'text/html', True),
        ('text/*,text/html', 'text/plain', True),
        ('text/*,text/html', 'text/html', True),
        ('application/json', 'text/plain', False),
        ('', 'text/plain', False),
        ('', '', False),
        ('text/plain', ',,', False),
        (',,', 'text/plain', False),
        ('text/plain', 'application/json,application/xml', False),
        ('application/json', '', False),
    ],
)
@pytest.mark.parametrize('compiled', [True, False])
def test_accepted_header(
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: _CleanModules,
    *,
    accept_value: str,
    media_type: str,
    request_accepts_type_by_header: bool,
    compiled: bool,
) -> None:
    """Ensure that selection of accepted type works correctly."""
    # Our setup, it can be compiled or not:
    monkeypatch.setenv('DMR_USE_COMPILED', str(int(compiled)))
    with clean_modules({'dmr.envs', 'dmr.compiled'}):
        from dmr.compiled import accepted_header  # noqa: PLC0415
        from dmr.envs import USE_COMPILED  # noqa: PLC0415

        assert USE_COMPILED is compiled
        if compiled:
            assert '_pure' not in accepted_header.__module__, (
                USE_COMPILED,
                compiled,
            )
        else:
            assert '_pure' in accepted_header.__module__, (
                USE_COMPILED,
                compiled,
            )
            assert isinstance(accepted_header, FunctionType)

        # The function itself:
        assert (
            accepted_header(accept_value, media_type)
            == request_accepts_type_by_header
        )
