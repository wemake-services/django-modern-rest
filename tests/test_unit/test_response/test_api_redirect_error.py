from http import HTTPStatus

import pytest
from django.core.exceptions import DisallowedRedirect
from django.utils.http import MAX_URL_REDIRECT_LENGTH

from dmr import APIRedirectError


def test_invalid_redirect_length() -> None:
    """We can't redirect to very long urls."""
    long_url = 'a' * MAX_URL_REDIRECT_LENGTH
    with pytest.raises(DisallowedRedirect, match='Unsafe redirect exceeding'):
        APIRedirectError(f'custom://{long_url}.com')


def test_invalid_redirect_scheme() -> None:
    """We can't redirect to untrusted protocols."""
    with pytest.raises(DisallowedRedirect, match='with protocol'):
        APIRedirectError('custom://url.com')


def test_invalid_status_code() -> None:
    """We can't redirect with wrong status code."""
    with pytest.raises(DisallowedRedirect, match='3xx statuses'):
        APIRedirectError('https://url.com', status_code=HTTPStatus.BAD_REQUEST)
    with pytest.raises(DisallowedRedirect, match='3xx statuses'):
        APIRedirectError('https://url.com', status_code=HTTPStatus.IM_USED)
