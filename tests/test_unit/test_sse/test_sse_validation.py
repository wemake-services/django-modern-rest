import dataclasses
import json
from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, TypeAlias

import pytest
from dirty_equals import IsStr
from django.http import HttpRequest, HttpResponse
from inline_snapshot import snapshot

from dmr import APIError, HeaderSpec, ResponseSpec
from dmr.errors import ErrorModel, format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
    sse,
)
from dmr.test import DMRAsyncRequestFactory

if TYPE_CHECKING:
    from tests.test_sse.conftest import (  # pyright: ignore[reportMissingImports]
        GetStreamingContent,
    )


_Serializers: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializers] = [
    PydanticSerializer,
]

MsgspecSerializer: type[BaseSerializer] | None
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    MsgspecSerializer = None
else:  # pragma: no cover
    assert MsgspecSerializer is not None
    serializers.append(MsgspecSerializer)


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    # When `msgspec` is missing, `@dataclass` is not supported:
    yield SSEvent(
        serializer.serialize(
            (
                {'email': 'first@example.com'}
                if MsgspecSerializer is None
                else _User(email='first@example.com')
            ),
            renderer=renderer,
        ),
    )
    yield SSEvent(
        serializer.serialize(
            (
                {'email': 'second@example.com'}
                if MsgspecSerializer is None
                else _User(email='second@example.com')
            ),
            renderer=renderer,
        ),
    )

    yield b'regular bytes'
    yield b'multiline\nbyte\nstring'
    yield 10


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_valid_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that valid sse produces valid results."""

    @sse(serializer)
    async def _valid_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_valid_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == (
        b'data: {"email":"first@example.com"}\r\n'
        b'\r\n'
        b'data: {"email":"second@example.com"}\r\n'
        b'\r\n'
        b'data: regular bytes\r\n'
        b'\r\n'
        b'data: multiline\r\n'
        b'data: byte\r\n'
        b'data: string\r\n'
        b'\r\n'
        b'data: 10\r\n'
        b'\r\n'
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'event',
    [
        {},
        {'a': 'b'},
        [],
        [1, 'a'],
        None,
        'abc',
        object(),
    ],
)
@pytest.mark.parametrize(
    ('options', 'expected'),
    [
        ({'validate_responses': True}, True),
        ({'validate_responses': True, 'validate_events': True}, True),
        ({'validate_responses': False, 'validate_events': True}, True),
        ({'validate_events': True}, True),
        ({}, True),
        ({'validate_responses': False}, False),
        ({'validate_events': False}, False),
        ({'validate_responses': False, 'validate_events': False}, False),
        ({'validate_responses': True, 'validate_events': False}, False),
    ],
)
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_event_type(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
    *,
    event: Any,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: bool,
) -> None:
    """Ensures that wrong event types are validated."""

    async def _wrong_type_events(
        serializer: type[BaseSerializer],
        renderer: Renderer,
    ) -> AsyncIterator[SSEData]:
        yield event

    @sse(serializer, **options)
    async def _wrong_type_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_wrong_type_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_wrong_type_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert (
        b'event: error\r\n' in await get_streaming_content(response)
    ) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('options', 'expected'),
    [
        ({'response_spec': None, 'validate_responses': True}, HTTPStatus.OK),
        ({'response_spec': None, 'validate_responses': False}, HTTPStatus.OK),
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    None,
                    status_code=HTTPStatus.CONFLICT,
                ),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                ),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                    headers={
                        'Cache-Control': HeaderSpec(),
                        'Connection': HeaderSpec(),
                        'X-Accel-Buffering': HeaderSpec(),
                    },
                ),
                'validate_responses': True,
            },
            HTTPStatus.OK,
        ),
        # Failures:
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
                'validate_responses': True,
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                    headers={},
                ),
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
@pytest.mark.parametrize('serializer', serializers)
async def test_main_response_validation_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: HTTPStatus,
) -> None:
    """Ensures that response validation can fail."""

    @sse(serializer, **options)
    async def _wrong_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_valid_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_wrong_sse.as_view()(request))

    assert response.status_code == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize('validate_responses', [True, False])
async def test_sse_api_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    validate_responses: bool,
) -> None:
    """Ensures that raising API errors is supported in SSE."""

    @sse(
        serializer,
        validate_responses=validate_responses,
        extra_responses=[
            ResponseSpec(ErrorModel, status_code=HTTPStatus.CONFLICT),
        ],
    )
    async def _valid_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        raise APIError(
            format_error('API Error'),
            status_code=HTTPStatus.CONFLICT,
        )

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CONFLICT, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'API Error'}],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_sse_api_error_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that raising API errors is supported in SSE."""

    @sse(serializer)
    async def _valid_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        raise APIError(
            format_error('API Error'),
            status_code=HTTPStatus.CONFLICT,
        )

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status code 409 is not specified '
                    'in the list of allowed status codes: [200, 422, 406]'
                ),
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
        HTTPMethod.OPTIONS,
        HTTPMethod.HEAD,
        HTTPMethod.TRACE,
        HTTPMethod.CONNECT,
    ],
)
async def test_sse_wrong_method(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    method: HTTPMethod,
) -> None:
    """Ensures that wrong methods are not supported."""

    @sse(serializer)
    async def _valid_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        raise NotImplementedError

    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers == {
        'Content-Type': 'application/json',
        'Allow': 'GET',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': IsStr(), 'type': 'not_allowed'}],
    })
