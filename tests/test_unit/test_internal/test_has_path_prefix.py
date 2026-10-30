import pytest

from dmr.internal.error_handlers import (
    has_path_prefix,
    normalize_languages,
    normalize_prefixes,
)
from dmr.test import DMRRequestFactory


@pytest.mark.parametrize(
    'path',
    [
        '/api/missing/',
        '/en-us/api/missing/',
        '/ru-ru/api/missing/',
        '/EN-US/api/missing/',
        # Not exact language codes, but they are supported by Django:
        '/en-gb/api/missing/',
        '/en/api/missing/',
        '/ru/api/missing/',
        '/kk/api/missing/',
    ],
)
def test_matching_paths(dmr_rf: DMRRequestFactory, *, path: str) -> None:
    """Ensure that paths with and without a language match the prefix."""
    request = dmr_rf.get(path)

    assert has_path_prefix(request, normalize_prefixes('api/'))


@pytest.mark.parametrize(
    'path',
    [
        '/other/missing/',
        '/apiary/missing/',
        '/shop/api/missing/',  # `shop` is not a language
        '/de/api/missing/',  # `de` is not in `LANGUAGES`
        '/en-us/other/missing/',
        '/en-us/apiary/missing/',
        '/en-us/en-us/api/missing/',  # only one language part is cut
        '/en-us//api/missing/',
        '/en-us',
        '/en-us/',
        '/',
    ],
)
def test_not_matching_paths(dmr_rf: DMRRequestFactory, *, path: str) -> None:
    """Ensure that other paths do not match the prefix."""
    request = dmr_rf.get(path)

    assert not has_path_prefix(request, normalize_prefixes('api/'))


def test_prefix_with_language(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that a prefix that starts with a language still works."""
    request = dmr_rf.get('/ru-ru/api/missing/')

    assert has_path_prefix(request, normalize_prefixes('ru-ru/api/'))
    assert not has_path_prefix(request, normalize_prefixes('en-us/api/'))


def test_many_prefixes(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that any of the prefixes can match after the language."""
    request = dmr_rf.get('/ru/v1/missing/')

    assert has_path_prefix(request, normalize_prefixes('api/', 'v1/'))


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        ('/api/missing/', True),
        ('/en/api/missing/', True),
        ('/ru/api/missing/', True),
        ('/RU/api/missing/', True),
        ('/en-gb/api/missing/', False),  # only `en` is allowed
        ('/en-us/api/missing/', False),
        ('/kk/api/missing/', False),  # `kk` is not in our list
        ('/de/api/missing/', False),
        ('/shop/api/missing/', False),
        ('/en/other/missing/', False),
    ],
)
def test_allowed_languages(
    dmr_rf: DMRRequestFactory,
    *,
    path: str,
    expected: bool,
) -> None:
    """Ensure that only exact languages from the list are allowed."""
    request = dmr_rf.get(path)

    assert (
        has_path_prefix(
            request,
            normalize_prefixes('api/'),
            normalize_languages(['en', 'ru']),
        )
        is expected
    )


def test_language_not_in_django(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that we do not check that the language is known to Django."""
    request = dmr_rf.get('/de/api/missing/')

    assert has_path_prefix(
        request,
        normalize_prefixes('api/'),
        normalize_languages(['de']),
    )


def test_empty_languages(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that no language is allowed with an empty list."""
    request = dmr_rf.get('/en-us/api/missing/')

    assert not has_path_prefix(
        request,
        normalize_prefixes('api/'),
        normalize_languages([]),
    )
    assert has_path_prefix(
        dmr_rf.get('/api/missing/'),
        normalize_prefixes('api/'),
        normalize_languages([]),
    )


def test_languages_are_lower_case() -> None:
    """Ensure that languages are normalized to lower case."""
    assert normalize_languages(['en', 'RU-ru']) == ('en', 'ru-ru')
    assert normalize_languages(None) is None
