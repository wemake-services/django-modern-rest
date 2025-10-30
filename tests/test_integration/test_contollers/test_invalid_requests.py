import json
from http import HTTPStatus

import pytest
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest.test import DMRAsyncClient, DMRClient


@pytest.mark.parametrize(
    'url',
    [
        reverse('api:parse_headers'),
        reverse('api:async_parse_headers'),
    ],
)
def test_parse_headers_error(dmr_client: DMRClient, *, url: str) -> None:
    """Ensure errors during parsing headers are caught."""
    response = dmr_client.post(
        url,
        data='{}',
        headers={'Content-Type': 'application/xml'},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'type': 'missing',
                'loc': ['parsed_headers', 'X-API-Token'],
                'msg': 'Field required',
                'input': {
                    'Cookie': '',
                    'Content-Length': '2',
                    'Content-Type': 'application/xml',
                },
            },
        ],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:parse_headers'),
        reverse('api:async_parse_headers'),
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
        headers={'Content-Type': 'application/xml'},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'type': 'missing',
                'loc': ['parsed_headers', 'X-API-Token'],
                'msg': 'Field required',
                'input': {
                    'Host': 'testserver',
                    'Content-Length': '2',
                    'Content-Type': 'application/xml',
                    'Cookie': '',
                },
            },
        ],
    })


def test_parse_headers_ignored_content_type(dmr_client: DMRClient) -> None:
    """Ensure that content-type is ignored for no `body` endpoints."""
    response = dmr_client.post(
        reverse('api:parse_headers'),
        data='{}',
        headers={'Content-Type': 'application/xml', 'X-API-Token': '123'},
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
        reverse('api:async_parse_headers'),
        data='{}',
        headers={'Content-Type': 'application/xml', 'X-API-Token': '123'},
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'X-API-Token': '123'}


def test_single_view_sync405(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that direct routes raise 405."""
    response = dmr_client.delete(
        reverse('api:parse_headers'),
        data='{}',
        headers={'Content-Type': 'application/xml', 'X-API-Token': '123'},
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': ("Method 'DELETE' is not allowed, allowed: ['POST']"),
    })


def test_single_view_async405(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that direct async routes raise 405."""
    response = dmr_client.delete(
        reverse('api:async_parse_headers'),
        data='{}',
        headers={'Content-Type': 'application/xml', 'X-API-Token': '123'},
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': ("Method 'DELETE' is not allowed, allowed: ['POST']"),
    })


def test_composed_view_sync405(dmr_client: DMRClient) -> None:
    """Ensure that composed async routes raise 405."""
    response = dmr_client.put(reverse('api:users'))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': "Method 'PUT' is not allowed, allowed: ['GET', 'POST']",
    })


def test_composed_view_async405(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that composed async routes raise 405."""
    response = dmr_client.delete(
        reverse('api:user_update', kwargs={'user_id': faker.random_int()}),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': "Method 'DELETE' is not allowed, allowed: ['PATCH', 'PUT']",
    })
