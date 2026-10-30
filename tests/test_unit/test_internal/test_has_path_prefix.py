import pytest

from dmr.internal.error_handlers import has_path_prefix, normalize_prefixes
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
