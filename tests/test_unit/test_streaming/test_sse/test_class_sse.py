from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from typing import TypeAlias

import pytest

from dmr import modify, validate
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

_EventsType: TypeAlias = SSEvent[dict[str, str] | bytes]


async def _valid_events() -> AsyncIterator[_EventsType]:
    yield SSEvent({})
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            _EventsType,
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        return self.to_stream(_valid_events())

    async def post(self) -> AsyncIterator[_EventsType]:
        return _valid_events()

    @modify(status_code=HTTPStatus.OK)
    async def put(self) -> AsyncIterator[_EventsType]:
        return _valid_events()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
async def test_valid_sse_different_methods(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that valid sse produces valid results."""
    endpoint = _ClassBasedSSE.api_endpoints[str(method)]
    assert endpoint.metadata.responses
    default_response = endpoint.metadata.responses[HTTPStatus.OK]
    assert default_response.headers
    assert default_response.headers.keys() == {
        'Cache-Control',
        'Connection',
        'X-Accel-Buffering',
    }

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
    assert await get_streaming_content(response) == (
        b'data: {}\r\n\r\ndata: multiline\r\ndata: byte\r\ndata: string\r\n\r\n'
    )


class _PostValidateSSE(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            _EventsType,
            content_type=ContentType.event_stream,
        ),
    )
    async def post(self) -> StreamingResponse:
        return self.to_stream(_valid_events())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
    ],
)
async def test_valid_sse_validate_post(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_PostValidateSSE.as_view()(request))

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
        b'data: {}\r\n\r\ndata: multiline\r\ndata: byte\r\ndata: string\r\n\r\n'
    )
