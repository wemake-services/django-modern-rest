import contextlib
import json
from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from typing import Any, Final, TypeAlias

import pytest
from dirty_equals import IsStr
from django.http import HttpRequest, HttpResponse
from inline_snapshot import snapshot

from dmr import APIError, ResponseSpec
from dmr.errors import ErrorModel, format_error
from dmr.exceptions import EndpointMetadataError, UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEResponse,
    SSEResponseSpec,
    SSEStreamingResponse,
    SSEvent,
    sse,
)
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

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


async def _valid_events() -> AsyncIterator[SSEvent[dict[str, str] | bytes]]:
    yield SSEvent({'email': 'first@example.com'})
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_valid_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that valid sse produces valid results."""

    @sse(serializer)
    async def _valid_sse(
        request: HttpRequest,
        context: SSEContext,
    ) -> SSEResponse[SSEvent[dict[str, str] | bytes]]:
        return SSEResponse(_valid_events())

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
    # Two renderers have a slightly different format:
    if MsgspecSerializer is None:  # pragma: no cover
        assert await get_streaming_content(response) == (
            b'data: {"email": "first@example.com"}\r\n'
            b'\r\n'
            b'data: multiline\r\n'
            b'data: byte\r\n'
            b'data: string\r\n'
            b'\r\n'
        )
    else:  # pragma: no cover
        assert await get_streaming_content(response) == (
            b'data: {"email":"first@example.com"}\r\n'
            b'\r\n'
            b'data: multiline\r\n'
            b'data: byte\r\n'
            b'data: string\r\n'
            b'\r\n'
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'event',
    [
        [],
        [1, 'a'],
        None,
        'abc',
        b'abc',
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
    *,
    event: Any,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: bool,
) -> None:
    """Ensures that wrong event types are validated."""

    async def _wrong_type_events() -> AsyncIterator[Any]:
        yield event

    @sse(serializer, **options)
    async def _wrong_type_sse(
        request: HttpRequest,
        context: SSEContext,
    ) -> SSEResponse[SSEvent[Any]]:
        return SSEResponse(_wrong_type_events())

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
    with (
        contextlib.nullcontext()
        if expected
        else pytest.raises(
            EndpointMetadataError,
            match='SSERenderer can only render SSE',
        )
    ):
        assert b'event: error\r\n' in await get_streaming_content(response)


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_event_generic_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that wrong event types are validated."""

    async def _wrong_type_events() -> AsyncIterator[Any]:
        yield SSEvent('string')

    @sse(serializer)
    async def _wrong_type_sse(
        request: HttpRequest,
        context: SSEContext,
    ) -> SSEResponse[SSEvent[int]]:
        return SSEResponse(_wrong_type_events())

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
    assert b'event: error\r\ndata: {"detail"' in await get_streaming_content(
        response,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_event_generic_validation_skip(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that missing type args skip the generic validation."""

    async def _wrong_type_events() -> AsyncIterator[Any]:
        yield SSEvent('string')

    @sse(serializer)
    async def _wrong_type_sse(
        request: HttpRequest,
        context: SSEContext,
    ) -> SSEResponse[SSEvent]:  # type: ignore[type-arg]
        return SSEResponse(_wrong_type_events())

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
    assert await get_streaming_content(response) == b'data: "string"\r\n\r\n'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('options', 'expected'),
    [
        ({'response_spec': None, 'validate_responses': True}, HTTPStatus.OK),
        ({'response_spec': None, 'validate_responses': False}, HTTPStatus.OK),
        (
            {
                'response_spec': SSEResponseSpec(None),
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
                'response_spec': SSEResponseSpec(
                    SSEvent[Any],
                ),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': SSEResponseSpec(SSEvent[Any]),
                'validate_responses': True,
            },
            HTTPStatus.OK,
        ),
        # Failures:
        (
            {
                'response_spec': SSEResponseSpec(
                    SSEvent[Any],
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
        context: SSEContext,
    ) -> SSEResponse[SSEvent[dict[str, str] | bytes]]:
        return SSEResponse(_valid_events())

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
        context: SSEContext,
    ) -> SSEResponse[Any]:
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
        context: SSEContext,
    ) -> SSEResponse[Any]:
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
        context: SSEContext,
    ) -> SSEResponse[Any]:
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


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_missing_event_model(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that missing event model raises."""
    with pytest.raises(UnsolvableAnnotationsError, match='event data model'):

        @sse(serializer)
        async def _valid_sse(
            request: HttpRequest,
            context: SSEContext,
        ) -> SSEResponse:  # type: ignore[type-arg]
            raise NotImplementedError


class _Events:
    async def __aiter__(self) -> AsyncIterator[SSEvent[int]]:
        yield SSEvent(1)
        yield SSEvent(2)


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_valid_sse_aiter_magic(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that valid sse produces valid results."""

    @sse(serializer)
    async def _valid_sse(
        request: HttpRequest,
        context: SSEContext,
    ) -> SSEResponse[SSEvent[int]]:
        return SSEResponse(_Events())  # type: ignore[arg-type]

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
        b'data: 1\r\n\r\ndata: 2\r\n\r\n'
    )
