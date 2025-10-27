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
_REQUEST_ID_ENDPOINT: Final = 'api:request_id'
_AUTHENTICATED_ENDPOINT: Final = 'api:authenticated'
_PROTECTED_ENDPOINT: Final = 'api:protected'

_TEST_USER_ID: Final = 456


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
def _dmr_client_csrf() -> DMRClient:
    """Customized version of :class:`django.test.Client` with csrf."""
    return DMRClient(enforce_csrf_checks=True)


@pytest.fixture
def _dmr_async_client_csrf() -> DMRAsyncClient:
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
    _dmr_client_csrf: DMRClient,  # noqa: PT019
    user_data: _UserData,
) -> None:
    """Tests forbidden request with csrf checks."""
    response = _dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
    )
    _assert_csrf_forbidden_response(response)


def test_csrf_with_token(
    _dmr_client_csrf: DMRClient,  # noqa: PT019
    user_data: _UserData,
) -> None:
    """Tests protected csrf request."""
    csrf_token = _get_csrf_token(_dmr_client_csrf)

    response = _dmr_client_csrf.post(
        reverse(_CSRF_TEST_ENDPOINT),
        data=user_data,
        headers={'X-CSRFToken': csrf_token},
    )
    _assert_successful_response(response, user_data)


@pytest.mark.asyncio
async def test_csrf_async_without_token(
    _dmr_async_client_csrf: DMRAsyncClient,  # noqa: PT019
    user_data: _UserData,
) -> None:
    """Tests forbidden async request with csrf checks."""
    response = await _dmr_async_client_csrf.post(
        reverse(_ASYNC_CSRF_TEST_ENDPOINT),
        data=user_data,
    )
    _assert_csrf_forbidden_response(response)


@pytest.mark.asyncio
async def test_csrf_async_with_token(
    _dmr_async_client_csrf: DMRAsyncClient,  # noqa: PT019
    user_data: _UserData,
) -> None:
    """Tests protected csrf async request."""
    csrf_token = await _get_csrf_token_async(_dmr_async_client_csrf)

    response = await _dmr_async_client_csrf.post(
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
    assert response.json() == {'detail': 'Rate limit exceeded'}


def test_request_id_middleware(dmr_client: DMRClient) -> None:
    """Test two-phase middleware: modifies request and response."""
    response = dmr_client.get(reverse(_REQUEST_ID_ENDPOINT))

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    request_id = response_data['request_id']

    assert response.headers['X-Request-ID'] == request_id


@pytest.mark.asyncio
async def test_request_id_middleware_async(
    dmr_async_client: DMRAsyncClient,
) -> None:
    """Test two-phase middleware with async controller."""
    response = await dmr_async_client.get(reverse(_REQUEST_ID_ENDPOINT))

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    request_id = response_data['request_id']

    assert response.headers['X-Request-ID'] == request_id


@pytest.mark.parametrize(
    ('token', 'expected_authenticated', 'expected_user_id'),
    [
        (None, False, 'anonymous'),  # No token
        ('invalid_token', False, 'anonymous'),  # Invalid format
        ('user_abc', False, 'anonymous'),  # Malformed user ID
        ('user_42', True, 42),  # Valid token
    ],
)
def test_auth_middleware(
    dmr_client: DMRClient,
    token: str | None,
    expected_authenticated: bool,  # noqa: FBT001
    expected_user_id: str | int,
) -> None:
    """Test auth middleware with various token scenarios."""
    headers = {'X-Auth-Token': token} if token else {}
    response = dmr_client.get(reverse(_AUTHENTICATED_ENDPOINT), headers=headers)

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    assert response_data['authenticated'] is expected_authenticated
    assert response_data['user_id'] == expected_user_id

    if expected_authenticated:
        assert response.headers['X-Authenticated'] == 'true'
    else:
        assert 'X-Authenticated' not in response.headers


@pytest.mark.asyncio
async def test_auth_middleware_async(dmr_async_client: DMRAsyncClient) -> None:
    """Test auth middleware with async controller."""
    response = await dmr_async_client.get(
        reverse(_AUTHENTICATED_ENDPOINT),
        headers={'X-Auth-Token': f'user_{_TEST_USER_ID}'},
    )

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    assert response_data['authenticated'] is True
    assert response_data['user_id'] == _TEST_USER_ID
    assert response.headers['X-Authenticated'] == 'true'


@pytest.mark.parametrize(
    ('token', 'expected_status', 'expected_detail'),
    [
        (None, HTTPStatus.UNAUTHORIZED, 'Authentication required'),
        ('invalid', HTTPStatus.UNAUTHORIZED, 'Authentication required'),
        ('user_abc', HTTPStatus.UNAUTHORIZED, 'Invalid authentication token'),
        (f'user_{_TEST_USER_ID}', HTTPStatus.OK, None),
    ],
)
def test_require_auth_middleware(
    dmr_client: DMRClient,
    token: str | None,
    expected_status: HTTPStatus,
    expected_detail: str | None,
) -> None:
    """Test require_auth middleware with various authentication scenarios."""
    headers = {'X-Auth-Token': token} if token else {}
    response = dmr_client.get(reverse(_PROTECTED_ENDPOINT), headers=headers)

    assert response.status_code == expected_status

    if expected_status == HTTPStatus.OK:
        response_data = response.json()
        assert response_data['user_id'] == _TEST_USER_ID
        assert response.headers['X-Authenticated'] == 'true'
    else:
        assert response.json() == {'detail': expected_detail}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('token', 'expected_status', 'expected_detail'),
    [
        (None, HTTPStatus.UNAUTHORIZED, 'Authentication required'),
        (f'user_{_TEST_USER_ID}', HTTPStatus.OK, None),
    ],
)
async def test_require_auth_middleware_async(
    dmr_async_client: DMRAsyncClient,
    token: str | None,
    expected_status: HTTPStatus,
    expected_detail: str | None,
) -> None:
    """Test require_auth middleware with async controller."""
    headers = {'X-Auth-Token': token} if token else {}
    response = await dmr_async_client.get(
        reverse(_PROTECTED_ENDPOINT),
        headers=headers,
    )

    assert response.status_code == expected_status

    if expected_status == HTTPStatus.OK:
        response_data = response.json()
        assert response_data['user_id'] == _TEST_USER_ID
        assert response.headers['X-Authenticated'] == 'true'
    else:
        assert response.json() == {'detail': expected_detail}


def _get_csrf_token(client: DMRClient) -> str:
    """Get CSRF token from the client."""
    response = client.get(reverse('api:csrf_token'))
    assert response.status_code == HTTPStatus.OK

    csrf_token = client.cookies.get('csrftoken')
    assert csrf_token is not None

    return csrf_token.value


async def _get_csrf_token_async(client: DMRAsyncClient) -> str:
    """Get CSRF token from the async client."""
    response = await client.get(reverse('api:csrf_token'))
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
    assert response.json() == {
        'detail': 'CSRF verification failed. Request aborted.',
    }
