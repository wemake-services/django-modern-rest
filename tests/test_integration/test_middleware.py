from http import HTTPStatus
from typing import Any, Final, TypedDict

import pytest
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRAsyncClient, DMRClient

_CSRF_TOKEN_ENDPOINT: Final = 'api:middlewares:csrf_token'  # noqa: S105
_CSRF_TEST_ENDPOINT: Final = 'api:middlewares:csrf_test'
_ASYNC_CSRF_TEST_ENDPOINT: Final = 'api:middlewares:async_csrf_test'
_CUSTOM_HEADER_ENDPOINT: Final = 'api:middlewares:custom_header'
_RATE_LIMITED_ENDPOINT: Final = 'api:middlewares:rate_limited'
_REQUEST_ID_ENDPOINT: Final = 'api:middlewares:request_id'
_LOGIN_REQUIRED_ENDPOINT: Final = 'api:middlewares:login_required'


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


@pytest.fixture
def dmr_client_csrf() -> DMRClient:
    """Customized version of :class:`django.test.Client` with csrf."""
    return DMRClient(enforce_csrf_checks=True)


@pytest.fixture
def dmr_async_client_csrf() -> DMRAsyncClient:
    """Customized version of :class:`django.test.AsyncClient` with csrf."""
    return DMRAsyncClient(enforce_csrf_checks=True)


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
    """Tests forbidden request with csrf checks."""
    response = dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
    )
    _assert_csrf_forbidden_response(response)


def test_csrf_with_token(
    dmr_client_csrf: DMRClient,
    user_data: _UserData,
) -> None:
    """Tests protected csrf request."""
    csrf_token = _get_csrf_token(dmr_client_csrf)

    response = dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
        headers={'X-CSRFToken': csrf_token},
    )
    _assert_successful_response(response, user_data)


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


@pytest.mark.asyncio
async def test_csrf_async_with_token(
    dmr_async_client_csrf: DMRAsyncClient,
    user_data: _UserData,
) -> None:
    """Tests protected csrf async request."""
    csrf_token = await _get_csrf_token_async(dmr_async_client_csrf)

    response = await dmr_async_client_csrf.post(
        reverse(_ASYNC_CSRF_TEST_ENDPOINT),
        data=user_data,
        headers={'X-CSRFToken': csrf_token},
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
    assert response.json() == snapshot({
        'detail': [{'msg': 'Rate limit exceeded'}],
    })


def test_request_id_middleware(dmr_client: DMRClient) -> None:
    """Test two-phase middleware: modifies request and response."""
    response = dmr_client.get(reverse(_REQUEST_ID_ENDPOINT))

    assert response.status_code == HTTPStatus.OK
    request_id = response.json()['request_id']

    assert response.headers['X-Request-ID'] == request_id


@pytest.mark.asyncio
async def test_request_id_middleware_async(
    dmr_async_client: DMRAsyncClient,
) -> None:
    """Test two-phase middleware with async controller."""
    response = await dmr_async_client.get(reverse(_REQUEST_ID_ENDPOINT))

    assert response.status_code == HTTPStatus.OK
    request_id = response.json()['request_id']

    assert response.headers['X-Request-ID'] == request_id


def _get_csrf_token(client: DMRClient) -> str:
    """Get CSRF token from the client."""
    response = client.get(reverse(_CSRF_TOKEN_ENDPOINT))
    assert response.status_code == HTTPStatus.OK

    csrf_token = client.cookies.get('csrftoken')
    assert csrf_token is not None

    return csrf_token.value


async def _get_csrf_token_async(client: DMRAsyncClient) -> str:
    """Get CSRF token from the async client."""
    response = await client.get(reverse(_CSRF_TOKEN_ENDPOINT))
    assert response.status_code == HTTPStatus.OK

    csrf_token = client.cookies.get('csrftoken')
    assert csrf_token is not None

    return csrf_token.value


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
    assert response.json() == snapshot({
        'detail': [{'msg': 'CSRF verification failed. Request aborted.'}],
    })


def test_login_required_unauthenticated(dmr_client: DMRClient) -> None:
    """Test Django's login_required returns 401 for unauthenticated users."""
    response = dmr_client.get(reverse(_LOGIN_REQUIRED_ENDPOINT))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == snapshot({
        'detail': [{'msg': 'Authentication credentials were not provided'}],
    })


def test_login_required_authenticated(
    dmr_client: DMRClient,
    django_user_model: Any,
    faker: Faker,
) -> None:
    """Test Django's login_required allows authenticated users."""
    username = faker.user_name()
    user = django_user_model.objects.create_user(
        username=username,
        password=faker.password(),
    )
    dmr_client.force_login(user)

    response = dmr_client.get(reverse(_LOGIN_REQUIRED_ENDPOINT))

    assert response.status_code == HTTPStatus.OK

    expected = {
        'username': username,
        'message': 'Successfully accessed protected resource',
    }
    assert response.json() == expected
