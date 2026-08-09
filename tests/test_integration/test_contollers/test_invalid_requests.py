import json
from http import HTTPStatus

import pytest
from dirty_equals import IsStr
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.security.http import basic_auth
from dmr.test import DMRAsyncClient, DMRClient


@pytest.mark.parametrize(
    'url',
    [
        reverse('api:controllers:parse_headers'),
        reverse('api:controllers:async_parse_headers'),
    ],
)
def test_parse_headers_error_sync(dmr_client: DMRClient, *, url: str) -> None:
    """Ensure errors during parsing headers are caught."""
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'Authorization': basic_auth('test', 'pass'),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_headers', 'X-API-Token'],
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:controllers:parse_headers'),
        reverse('api:controllers:async_parse_headers'),
    ],
)
async def test_parse_headers_error_async(
    dmr_async_client: DMRAsyncClient,
    *,
    url: str,
) -> None:
    """Ensure errors during async parsing headers are caught."""
    response = await dmr_async_client.post(
        url,
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'Authorization': basic_auth('test', 'pass'),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_headers', 'X-API-Token'],
                'type': 'value_error',
            },
        ],
    })


def test_parse_headers_ignored_content_type(dmr_client: DMRClient) -> None:
    """Ensure that content-type is ignored for no `body` endpoints."""
    response = dmr_client.post(
        reverse('api:controllers:parse_headers'),
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'X-API-Token': '123',
            'Authorization': basic_auth('test', 'pass'),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'X-API-Token': '123'}


@pytest.mark.asyncio
async def test_parse_headers_ignored_async_content_type(
    dmr_async_client: DMRAsyncClient,
) -> None:
    """Ensure that content-type is ignored for no `body` async endpoints."""
    response = await dmr_async_client.post(
        reverse('api:controllers:async_parse_headers'),
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'X-API-Token': '123',
            'Authorization': basic_auth('test', 'pass', prefix=''),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'X-API-Token': '123'}


@pytest.mark.parametrize(
    'body',
    [
        b'"\xff"',
        b'{"username": "\xff"}',
    ],
)
def test_body_with_invalid_utf8(dmr_client: DMRClient, *, body: bytes) -> None:
    """Ensure that non-utf8 bytes inside json strings are caught."""
    response = dmr_client.post(
        reverse('api:controllers:constrained_user_create'),
        data=body,
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    # The reported position differs between parsers, `msgspec` reports it
    # relative to the string being decoded, while `json` reports
    # the absolute one:
    assert response.json() == {
        'detail': [
            {
                'msg': IsStr(
                    regex=(
                        r"'utf-8' codec can't decode byte 0xff "
                        r'in position \d+: invalid start byte'
                    ),
                ),
                'type': 'value_error',
            },
        ],
    }


def test_single_view_sync405(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that direct routes raise 405."""
    response = dmr_client.delete(
        reverse('api:controllers:parse_headers'),
        data='{}',
        headers={'Content-Type': 'application/xml', 'X-API-Token': '123'},
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Method 'DELETE' is not allowed, allowed: ['POST']",
                'type': 'not_allowed',
            },
        ],
    })


def test_single_view_i18n_sync405(
    dmr_client: DMRClient,
    faker: Faker,
    reset_language: None,
) -> None:
    """Ensure that direct routes raise 405 with i18n support."""
    response = dmr_client.delete(
        reverse('api:controllers:parse_headers'),
        data='{}',
        headers={'Accept-Language': 'ru'},
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Метод 'DELETE' не разрешён, разрешённые: ['POST']",
                'type': 'not_allowed',
            },
        ],
    })


def test_single_view_async405(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that direct async routes raise 405."""
    response = dmr_client.delete(
        reverse('api:controllers:async_parse_headers'),
        data='{}',
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Method 'DELETE' is not allowed, allowed: ['POST']",
                'type': 'not_allowed',
            },
        ],
    })


def test_composed_view_sync405(dmr_client: DMRClient) -> None:
    """Ensure that composed async routes raise 405."""
    response = dmr_client.put(reverse('api:controllers:users'))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Method 'PUT' is not allowed, allowed: ['GET', 'POST']",
                'type': 'not_allowed',
            },
        ],
    })


def test_composed_view_async405(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that composed async routes raise 405."""
    response = dmr_client.delete(
        reverse(
            'api:controllers:user_update',
            kwargs={'user_id': faker.random_int()},
        ),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    "Method 'DELETE' is not allowed, allowed: ['PATCH', 'PUT']"
                ),
                'type': 'not_allowed',
            },
        ],
    })
