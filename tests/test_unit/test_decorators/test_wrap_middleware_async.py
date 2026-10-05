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

# ETags are quoted strings (RFC 9110), Django ignores `If-None-Match`
# values without quotes:
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


@pytest.mark.asyncio
async def test_async_aware_decorator(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that Django's async decorators wrap async controllers."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncCatalogController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Content-Type': 'application/json',
        'ETag': '"catalog-42"',
    }
    assert json.loads(response.content) == snapshot(['book', 'pen'])


@pytest.mark.asyncio
async def test_async_aware_decorator_response(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that Django's async decorators can answer on their own."""
    request = dmr_async_rf.get('/whatever/', headers={'If-None-Match': _ETAG})

    response = await dmr_async_rf.wrap(
        _AsyncCatalogController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.headers == {
        'ETag': '"catalog-42"',
        'Content-Type': 'application/json',
    }
    assert response.content == b''


_SHORT_CIRCUIT_HEADER: Final = 'X-Short-Circuit'


def _plain_middleware(
    get_response: Callable[[HttpRequest], Any],
) -> Callable[[HttpRequest], Any]:
    def decorator(request: HttpRequest) -> Any:
        if request.headers.get(_SHORT_CIRCUIT_HEADER):
            # A regular response, even for async controllers:
            return HttpResponse(status=HTTPStatus.NO_CONTENT)
        # A coroutine for async controllers:
        return get_response(request)

    return decorator


@wrap_middleware(
    _plain_middleware,
    ResponseSpec(None, status_code=HTTPStatus.NO_CONTENT),
)
def _plain_json(response: HttpResponse) -> HttpResponse:
    return response


@final
@_plain_json
class _AsyncPlainController(Controller[PydanticSerializer]):
    responses = _plain_json.responses

    async def get(self) -> str:
        return 'inside'


@pytest.mark.asyncio
async def test_plain_middleware_function(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that plain middleware functions still wrap async controllers."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_AsyncPlainController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot('inside')


@pytest.mark.asyncio
async def test_plain_middleware_function_response(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that plain middleware functions can answer on their own."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={_SHORT_CIRCUIT_HEADER: 'true'},
    )

    response = await dmr_async_rf.wrap(_AsyncPlainController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
