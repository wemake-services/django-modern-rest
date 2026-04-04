import sys
from collections.abc import Callable, Iterator, Set
from contextlib import AbstractContextManager, contextmanager
from types import ModuleType
from typing import Final, TypeAlias

import pytest
from django.http import HttpRequest
from pytest_codspeed import BenchmarkFixture

_CleanModules: TypeAlias = Callable[
    [set[str]],
    AbstractContextManager[dict[str, ModuleType]],
]

_COMPILED_MODULES: Final = frozenset((
    'dmr.envs',
    'dmr.compiled',
    'dmr._compiled',
))


@pytest.fixture
def clean_modules() -> _CleanModules:
    """Fixture to clean required modules."""

    @contextmanager
    def factory(names: Set[str]) -> Iterator[dict[str, ModuleType]]:
        orig_modules = {}
        prefixes = tuple(f'{name}.' for name in names)
        for modname in list(sys.modules):
            if modname in names or modname.startswith(prefixes):
                orig_modules[modname] = sys.modules.pop(modname)

        yield orig_modules

        sys.modules.update(orig_modules)

    return factory


_ACCEPTED_TYPE_CASES: Final = (
    ('text/plain', ['text/plain'], 'text/plain'),
    ('text/plain', ['text/html'], None),
    ('text/*', ['text/html'], 'text/html'),
    ('*/*', ['text/html'], 'text/html'),
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
    ('text/*,text/html', ['text/plain', 'text/html'], 'text/html'),
)


def test_negotiation_compiled(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: _CleanModules,
) -> None:
    """Test compiled version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '1')

    with clean_modules(_COMPILED_MODULES):
        from dmr._compiled import negotiation  # noqa: PLC0415, PLC2701

        assert negotiation.__file__.endswith('.so')

        from dmr.compiled import accepted_type  # noqa: PLC0415

        assert '_pure' not in accepted_type.__module__

        @benchmark
        def factory() -> None:
            for accept, provided_types, expected in _ACCEPTED_TYPE_CASES:
                assert accepted_type(accept, provided_types) == expected


def test_negotiation_raw(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: _CleanModules,
) -> None:
    """Test raw version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '0')

    with clean_modules(_COMPILED_MODULES):
        from dmr.compiled import accepted_type  # noqa: PLC0415

        assert '_pure' in accepted_type.__module__

        @benchmark
        def factory() -> None:
            for accept, provided_types, expected in _ACCEPTED_TYPE_CASES:
                assert accepted_type(accept, provided_types) == expected


def test_negotiation_django_native(
    benchmark: BenchmarkFixture,
) -> None:
    """Test Django native version of the negotiation protocol."""

    @benchmark
    def factory() -> None:
        for accept, provided_types, _expected in _ACCEPTED_TYPE_CASES:
            request = HttpRequest()
            request.META = {'HTTP_ACCEPT': accept}
            request.get_preferred_type(provided_types)
