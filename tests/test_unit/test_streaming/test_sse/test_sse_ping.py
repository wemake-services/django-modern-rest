import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus

import pydantic
import pytest

from dmr import Body
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _BodyModel(pydantic.BaseModel):
    produce_last: bool = False


class _PingSSE(SSEController[PydanticSerializer]):
    streaming_ping_seconds = 0.2

    async def post(
        self,
        parsed_body: Body[_BodyModel],
    ) -> AsyncIterator[SSEvent[int]]:
        return self._valid_events(produce_last=parsed_body.produce_last)

    async def _valid_events(
        self,
        *,
        produce_last: bool,
    ) -> AsyncIterator[SSEvent[int]]:
        ping = self.streaming_ping_seconds
        assert isinstance(ping, float)

        yield SSEvent(1)
        await asyncio.sleep(ping + 0.1)  # one ping
        yield SSEvent(2)
        await asyncio.sleep((2 * ping) + 0.1)  # two pings
        if produce_last:
            yield SSEvent(3)


@pytest.mark.asyncio
async def test_sse_ping(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.post('/whatever/', data={})

    response = await dmr_async_rf.wrap(_PingSSE.as_view()(request))

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
        b'data: 1\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b'data: 2\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
    )


@pytest.mark.asyncio
async def test_sse_ping_with_last(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.post('/whatever/', data={'produce_last': True})

    response = await dmr_async_rf.wrap(_PingSSE.as_view()(request))

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
        b'data: 1\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b'data: 2\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b'data: 3\r\n'
        b'\r\n'
    )
