"""Tests for middleware integration (CSRF, custom headers, rate limiting)."""

from http import HTTPStatus
from typing import Any, Final, TypedDict

import pytest
from django.urls import reverse
from faker import Faker

from django_modern_rest.test import DMRAsyncClient, DMRClient

_CSRF_TEST_ENDPOINT: Final = 'api:csrf_test'
_ASYNC_CSRF_TEST_ENDPOINT: Final = 'api:async_csrf_test'
_CUSTOM_HEADER_ENDPOINT: Final = 'api:custom_header'
_RATE_LIMITED_ENDPOINT: Final = 'api:rate_limited'


class _UserData(TypedDict):
    """Test user data structure."""

    email: str
    age: int


@pytest.fixture
def user_data(faker: Faker) -> _UserData:
    """Generate test user data with email and age."""
    return _UserData(
        email=faker.email(),
        age=faker.random_int(min=1, max=120),  # noqa: WPS432
    )


def test_csrf_protection_default_off(
    dmr_client: DMRClient,
    user_data: _UserData,
) -> None:
    """Tests success request when CSRF is off."""
    response = dmr_client.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
    )

    _assert_successful_response(response, user_data)


def test_csrf_without_token(
    dmr_client_csrf: DMRClient,
    user_data: _UserData,
) -> None:
    """Tests frobidden request with csrf checks."""
    response = dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
    )

    _assert_csrf_forbidden_response(response)


@pytest.mark.asyncio
async def test_csrf_async_without_token(
    dmr_async_client_csrf: DMRAsyncClient,
    user_data: _UserData,
) -> None:
    """Tests forbidden async request with csrf checks."""
    response = await dmr_async_client_csrf.post(
        reverse(_ASYNC_CSRF_TEST_ENDPOINT),
        data=user_data,
    )

    _assert_csrf_forbidden_response(response)


def test_csrf_with_token(
    dmr_client_csrf: DMRClient,
    user_data: _UserData,
) -> None:
    """Tests protected csrf request."""
    response = dmr_client_csrf.get(reverse('api:csrf_token'))
    assert response.status_code == HTTPStatus.OK

    csrf_token = dmr_client_csrf.cookies.get('csrftoken')
    assert csrf_token is not None

    response = dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
        headers={'X-CSRFToken': csrf_token.value},
    )

    _assert_successful_response(response, user_data)


@pytest.mark.asyncio
async def test_csrf_async_with_token(
    dmr_async_client_csrf: DMRAsyncClient,
    user_data: _UserData,
) -> None:
    """Tests protected csrf async request."""
    response = await dmr_async_client_csrf.get(reverse('api:csrf_token'))
    assert response.status_code == HTTPStatus.OK

    csrf_token = dmr_async_client_csrf.cookies.get('csrftoken')
    assert csrf_token is not None

    response = await dmr_async_client_csrf.post(
        reverse(_ASYNC_CSRF_TEST_ENDPOINT),
        data=user_data,
        headers={'X-CSRFToken': csrf_token.value},
    )

    _assert_successful_response(response, user_data)


def test_custom_header_middleware_sync(dmr_client: DMRClient) -> None:
    """Test that custom header middleware works with sync controller."""
    response = dmr_client.get(reverse(_CUSTOM_HEADER_ENDPOINT))

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'message': 'Success'}
    assert response.headers['X-Custom-Header'] == 'CustomValue'


def test_rate_limit_middleware_allowed(
    dmr_client: DMRClient,
    user_data: _UserData,
) -> None:
    """Test that request passes when not rate limited."""
    response = dmr_client.post(
        reverse(_RATE_LIMITED_ENDPOINT),
        data=user_data,
    )

    _assert_successful_response(response, user_data)


def test_rate_limit_middleware_blocked(
    dmr_client: DMRClient,
    user_data: _UserData,
) -> None:
    """Test rate limit middleware blocks request and callback handles it."""
    response = dmr_client.post(
        reverse(_RATE_LIMITED_ENDPOINT),
        data=user_data,
        headers={'X-Rate-Limited': 'true'},
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'detail': 'Rate limit exceeded'}


def _assert_successful_response(
    response: Any,
    expected_data: _UserData,
) -> None:
    """Assert that response is successful with correct headers and body."""
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == expected_data


def _assert_csrf_forbidden_response(response: Any) -> None:
    """Assert that response is CSRF forbidden."""
    assert response.status_code == HTTPStatus.FORBIDDEN, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'detail': 'CSRF verification failed. Request aborted.',
    }
