from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest

from dmr import validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.sse import (
    SSEResponseSpec,
    SSEStreamingResponse,
    SSEvent,
)
from dmr.sse.builder import _BaseSSEController
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


async def _valid_events() -> AsyncIterator[SSEvent[dict[str, str] | bytes]]:
    yield SSEvent({'email': 'first@example.com'})
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)


class _ValidateBasedSSE(_BaseSSEController[PydanticSerializer]):
    @validate(SSEResponseSpec(SSEvent[dict[str, str] | bytes]))
    async def get(self) -> SSEStreamingResponse:
        return self.to_sse_response(_valid_events())


@pytest.mark.asyncio
async def test_valid_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ValidateBasedSSE.as_view()(request))

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
        b'data: multiline\r\n'
        b'data: byte\r\n'
        b'data: string\r\n'
        b'\r\n'
    )
