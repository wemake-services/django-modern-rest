from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest
from django.http import HttpRequest
from pytest_codspeed import BenchmarkFixture

if TYPE_CHECKING:
    from conftest import CleanModules


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
    clean_modules: CleanModules,
) -> None:
    """Test compiled version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '1')

    with clean_modules():
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
    clean_modules: CleanModules,
) -> None:
    """Test raw version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '0')

    with clean_modules():
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
