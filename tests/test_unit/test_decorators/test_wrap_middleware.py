import inspect
import json
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any, Final, final

import pytest
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from inline_snapshot import snapshot

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.response import build_response
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_MODE_HEADER: Final = 'X-Mode'


def _middleware(
    get_response: Callable[[HttpRequest], Any],
) -> Callable[[HttpRequest], Any]:
    def decorator(request: HttpRequest) -> Any:
        mode = request.headers.get(_MODE_HEADER)
        if mode == 'invalid':
            return HttpResponse(
                'not json',
                status=HTTPStatus.IM_A_TEAPOT,
                content_type='text/plain',
            )
        if mode == 'undocumented':
            return HttpResponse(status=HTTPStatus.TOO_MANY_REQUESTS)
        if mode == 'valid':
            return HttpResponse(status=HTTPStatus.IM_A_TEAPOT)

        response = get_response(request)
        if inspect.isawaitable(response):
            return _add_header_async(response)
        return _add_header(response)

    return decorator


def _add_header(response: HttpResponseBase) -> HttpResponseBase:
    # This header is not documented, validation would fail on it:
    response['X-Extra'] = 'added'
    return response


async def _add_header_async(
    response: Awaitable[HttpResponseBase],
) -> HttpResponseBase:
    return _add_header(await response)


@wrap_middleware(
    _middleware,
    ResponseSpec(ErrorModel, status_code=HTTPStatus.IM_A_TEAPOT),
)
def _middleware_json(response: HttpResponse) -> HttpResponse:
    if response.content:
        return response  # does not convert invalid responses
    return build_response(
        PydanticSerializer,
        raw_data=format_error('Teapot'),
        status_code=HTTPStatus.IM_A_TEAPOT,
    )


@final
@_middleware_json
class _SyncController(Controller[PydanticSerializer]):
    responses = _middleware_json.responses

    def get(self) -> str:
        return 'inside'


@final
@_middleware_json
class _AsyncController(Controller[PydanticSerializer]):
    responses = _middleware_json.responses

    async def get(self) -> str:
        return 'inside'


@final
@_middleware_json
class _NoValidationController(Controller[PydanticSerializer]):
    responses = _middleware_json.responses
    validate_responses = False

    def get(self) -> str:
        raise NotImplementedError


def test_invalid_middleware_response(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that middleware responses are validated."""
    request = dmr_rf.get('/whatever/', headers={_MODE_HEADER: 'invalid'})

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
    })
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    "Response content type 'text/plain' "
                    'is not listed as a possible to be returned '
                    "['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.asyncio
async def test_invalid_middleware_response_async(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that middleware responses are validated for async views."""
    request = dmr_async_rf.get('/whatever/', headers={_MODE_HEADER: 'invalid'})

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
    })
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    "Response content type 'text/plain' "
                    'is not listed as a possible to be returned '
                    "['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


def test_undocumented_middleware_status(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that middleware status codes must be documented."""
    request = dmr_rf.get('/whatever/', headers={_MODE_HEADER: 'undocumented'})

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status code 429 is not specified in the list '
                    'of allowed status codes: [418, 200, 406, 422]'
                ),
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.asyncio
async def test_undocumented_middleware_status_async(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that middleware status codes must be documented for async."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={_MODE_HEADER: 'undocumented'},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status code 429 is not specified in the list '
                    'of allowed status codes: [418, 200, 406, 422]'
                ),
                'type': 'value_error',
            },
        ],
    })


def test_valid_middleware_response(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that converted middleware responses pass validation."""
    request = dmr_rf.get('/whatever/', headers={_MODE_HEADER: 'valid'})

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
    })
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Teapot'}],
    })


@pytest.mark.asyncio
async def test_valid_middleware_response_async(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that converted middleware responses pass validation in async."""
    request = dmr_async_rf.get('/whatever/', headers={_MODE_HEADER: 'valid'})

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
    })
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Teapot'}],
    })


def test_view_response_is_validated_once(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that view responses are not validated again."""
    request = dmr_rf.get('/whatever/')

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
        'X-Extra': 'added',
    })
    assert json.loads(response.content) == snapshot('inside')


@pytest.mark.asyncio
async def test_view_response_is_validated_once_async(
    *,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async view responses are not validated again."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert dict(response.headers) == snapshot({
        'Content-Type': 'application/json',
        'X-Extra': 'added',
    })
    assert json.loads(response.content) == snapshot('inside')


def test_middleware_response_without_validation(
    *,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that ``validate_responses = False`` is respected."""
    request = dmr_rf.get('/whatever/', headers={_MODE_HEADER: 'invalid'})

    response = _NoValidationController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT
    assert dict(response.headers) == snapshot({'Content-Type': 'text/plain'})
    assert response.content == b'not json'
