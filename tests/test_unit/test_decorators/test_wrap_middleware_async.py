import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Final, final

import pytest
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import condition
from inline_snapshot import snapshot

from dmr import Controller, HeaderSpec, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory

_ETAG: Final = '"catalog-42"'


def _catalog_etag(request: HttpRequest, **kwargs: object) -> str:
    return _ETAG


@wrap_middleware(
    condition(etag_func=_catalog_etag),
    ResponseSpec(
        None,
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={'ETag': HeaderSpec()},
    ),
)
def _catalog_etag_json(response: HttpResponse) -> HttpResponse:
    response['Content-Type'] = 'application/json'
    return response


@final
@_catalog_etag_json
class _AsyncCatalogController(Controller[PydanticSerializer]):
    responses = _catalog_etag_json.responses

    async def get(self) -> list[str]:
        return ['book', 'pen']


def _passthrough_middleware(
    get_response: Callable[[HttpRequest], Any],
) -> Callable[[HttpRequest], Any]:
    def decorator(request: HttpRequest) -> Any:
        # Plain function middleware gets a coroutine for async controllers:
        return get_response(request)

    return decorator


@wrap_middleware(
    _passthrough_middleware,
    ResponseSpec(None, status_code=HTTPStatus.NO_CONTENT),
)
def _passthrough_json(response: HttpResponse) -> HttpResponse:
    raise NotImplementedError


@final
@_passthrough_json
class _AsyncPassthroughController(Controller[PydanticSerializer]):
    responses = _passthrough_json.responses

    async def get(self) -> str:
        return 'inside'


@pytest.mark.asyncio
async def test_async_aware_decorator(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that Django's async decorators wrap async controllers."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncCatalogController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
        'ETag': '"catalog-42"',
    })
    assert json.loads(response.content) == snapshot(['book', 'pen'])


@pytest.mark.asyncio
async def test_async_aware_decorator_response(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that Django's async decorators can answer on their own."""
    request = dmr_async_rf.get('/whatever/', headers={'If-None-Match': _ETAG})

    response = await dmr_async_rf.wrap(
        _AsyncCatalogController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert dict(response.headers) == snapshot({
        'ETag': '"catalog-42"',
        'Content-Type': 'application/json',
    })
    assert response.content == b''


@pytest.mark.asyncio
async def test_sync_middleware_function(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that plain middleware functions still wrap async controllers."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncPassthroughController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
    })
    assert json.loads(response.content) == snapshot('inside')
