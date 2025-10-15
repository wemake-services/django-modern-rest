from http import HTTPStatus

import pytest
from django.urls import reverse
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
                'loc': ['X-API-Token'],
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
                'loc': ['X-API-Token'],
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
