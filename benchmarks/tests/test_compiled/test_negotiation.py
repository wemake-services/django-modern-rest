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


_REQUEST_ACCEPTS_CASES: Final = (
    ('text/plain', 'text/plain', True),
    ('text/plain', 'text/html', False),
    ('text/*', 'text/html', True),
    ('*/*', 'text/html', True),
    ('text/plain;p=test', 'text/plain;p=test', True),
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
    ('application/json', '', False),
)


def test_accepted_header_compiled(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
) -> None:
    """Test compiled version of accepted_header."""

    monkeypatch.setenv('DMR_USE_COMPILED', '1')

    with clean_modules():
        from dmr._compiled import negotiation  # noqa: PLC0415, PLC2701
        from dmr.compiled import accepted_header  # noqa: PLC0415

        assert negotiation.__file__.endswith('.so')
        assert '_pure' not in accepted_header.__module__

        @benchmark
        def factory() -> None:
            for accept, media_type, expected in _REQUEST_ACCEPTS_CASES:
                assert accepted_header(accept, media_type) == expected


def test_accepted_header_raw(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
) -> None:
    """Test raw version of accepted_header."""

    monkeypatch.setenv('DMR_USE_COMPILED', '0')

    with clean_modules():
        from dmr.compiled import accepted_header  # noqa: PLC0415

        assert '_pure' in accepted_header.__module__

        @benchmark
        def factory() -> None:
            for accept, media_type, expected in _REQUEST_ACCEPTS_CASES:
                assert accepted_header(accept, media_type) == expected


def test_accepted_header_django_native(
    benchmark: BenchmarkFixture,
) -> None:
    """Test Django native version of request.accepts."""

    @benchmark
    def factory() -> None:
        for accept, media_type, expected in _REQUEST_ACCEPTS_CASES:
            request = HttpRequest()
            request.META = {'HTTP_ACCEPT': accept}
            assert request.accepts(media_type) == expected
