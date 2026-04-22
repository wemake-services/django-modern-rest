import contextlib
import json
from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from typing import Any, Final, TypeAlias

import pytest
from dirty_equals import IsStr
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import APIError, ResponseSpec, modify, validate
from dmr.errors import ErrorModel, format_error
from dmr.exceptions import DataRenderingError, EndpointMetadataError
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.sse import SSEController, SSEvent
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


_EventsType: TypeAlias = SSEvent[dict[str, str] | bytes]


async def _valid_events() -> AsyncIterator[_EventsType]:
    yield SSEvent({'email': 'first@example.com'})
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)  # pyrefly: ignore[no-matching-overload]


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_valid_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that valid sse produces valid results."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[_EventsType]:
            return _valid_events()

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
        b'data: multiline\r\n'
        b'data: byte\r\n'
        b'data: string\r\n'
        b'\r\n'
    )


_OptionFlagsType: TypeAlias = tuple[
    tuple[dict[str, bool], bool],
    ...,
]
_OPTION_FLAGS: Final[_OptionFlagsType] = (
    ({'validate_responses': True}, True),
    ({'validate_responses': True, 'validate_events': True}, True),
    ({'validate_responses': False, 'validate_events': True}, True),
    ({'validate_events': True}, True),
    ({}, True),
    ({'validate_responses': False}, False),
    ({'validate_events': False}, False),
    ({'validate_responses': False, 'validate_events': False}, False),
    ({'validate_responses': True, 'validate_events': False}, False),
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
    _OPTION_FLAGS,
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

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        validate_responses = options.get('validate_responses')
        validate_events = options.get('validate_events')

        async def get(self) -> AsyncIterator[_EventsType]:
            return _wrong_type_events()

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
            DataRenderingError,
            match='SSERenderer can only render SSE',
        )
    ):
        assert b'event: error\r\n' in await get_streaming_content(response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('options', 'expected'),
    _OPTION_FLAGS,
)
@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_event_type_endpoint(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: bool,
    method: HTTPMethod,
) -> None:
    """Ensures that wrong event types are validated."""

    async def _wrong_type_events() -> AsyncIterator[Any]:
        yield

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        @modify(
            validate_events=options.get('validate_events'),
            validate_responses=options.get('validate_responses'),
        )
        async def get(self) -> AsyncIterator[_EventsType]:
            return _wrong_type_events()

        @validate(
            streaming_response_spec(
                _EventsType,
                content_type=ContentType.event_stream,
            ),
            validate_events=options.get('validate_events'),
            validate_responses=options.get('validate_responses'),
        )
        async def post(self) -> StreamingResponse:
            return self.to_stream(_wrong_type_events())

    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
            DataRenderingError,
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

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[_EventsType]:
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[Any]]:
            yield SSEvent('string')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent]:  # type: ignore[type-arg]
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[str]]:
            yield SSEvent('string')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
@pytest.mark.parametrize('serializer', serializers)
async def test_event_validation_from_settings(
    dmr_async_rf: DMRAsyncRequestFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that global settings can be used to disable event validation."""
    settings.DMR_SETTINGS = {
        Settings.validate_events: False,
    }

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[Any]]:
            yield SSEvent('string')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
@pytest.mark.parametrize('serializer', serializers)
async def test_event_response_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that wrong response spec raises 422."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        @validate(ResponseSpec(str, status_code=HTTPStatus.OK, streaming=True))
        async def get(self) -> StreamingResponse:
            return self.to_stream(_valid_events())

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json'}


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize('validate_responses', [True, False, None])
@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
async def test_sse_api_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    validate_responses: bool | None,
    method: HTTPMethod,
) -> None:
    """Ensures that raising API errors is supported in SSE."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        responses = (
            ResponseSpec(
                return_type=ErrorModel,
                status_code=HTTPStatus.CONFLICT,
            ),
        )

        @modify(validate_responses=validate_responses)
        async def get(self) -> AsyncIterator[SSEvent[str]]:
            raise APIError(
                format_error('API Error'),
                status_code=HTTPStatus.CONFLICT,
            )

        async def post(self) -> HttpResponse:
            return self.to_error(
                format_error('API Error'),
                status_code=HTTPStatus.CONFLICT,
            )

    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CONFLICT, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'API Error'}],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize('validate_responses', [True, None])
async def test_sse_api_error_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    validate_responses: bool | None,
) -> None:
    """Ensures that raising API errors is supported in SSE."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        @modify(validate_responses=validate_responses)
        async def get(self) -> AsyncIterator[SSEvent[str]]:
            raise APIError(
                format_error('API Error'),
                status_code=HTTPStatus.CONFLICT,
            )

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

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

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent[str]]:
            raise NotImplementedError

    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

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
    """Ensures that missing event model defaults to ``Any`` when non strict."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        validate_responses = False
        validate_events = False

        @validate(
            streaming_response_spec(
                int,
                status_code=HTTPStatus.CREATED,
                content_type=ContentType.event_stream,
            ),
        )
        async def get(self) -> StreamingResponse:
            return self.to_stream(self._events())

        async def _events(self) -> AsyncIterator[SSEvent[str]]:
            yield SSEvent('string')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
@pytest.mark.parametrize('serializer', serializers)
async def test_missing_event_model_strict(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that missing event model raise when ``validate_events``."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        validate_responses = False
        validate_events = True

        @validate(
            streaming_response_spec(
                int,
                status_code=HTTPStatus.CREATED,
                content_type=ContentType.event_stream,
            ),
        )
        async def get(self) -> StreamingResponse:
            return self.to_stream(self._events())

        async def _events(self) -> AsyncIterator[SSEvent[str]]:
            yield SSEvent('string')  # pragma: no cover

    request = dmr_async_rf.get('/whatever/')

    with pytest.raises(EndpointMetadataError, match='OK: 200'):
        await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))


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

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return aiter(_Events())

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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
