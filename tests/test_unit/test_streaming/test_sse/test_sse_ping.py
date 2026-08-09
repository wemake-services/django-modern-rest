import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pydantic
import pytest
from typing_extensions import override

from dmr import Body
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _BodyModel(pydantic.BaseModel):
    produce_last: bool = False


class _PingSSE(SSEController[PydanticSerializer]):
    # We don't sleep between the events, we wait for the exact
    # number of pings instead. Otherwise, the test would be flaky
    # on slow machines: a late event might miss its ping window.
    streaming_ping_seconds = 0.1

    _pings: int
    _new_ping: asyncio.Event

    async def post(
        self,
        parsed_body: Body[_BodyModel],
    ) -> AsyncIterator[SSEvent[int]]:
        self._pings = 0
        self._new_ping = asyncio.Event()
        return self._valid_events(produce_last=parsed_body.produce_last)

    @override
    def ping_event(self) -> Any | None:
        self._pings += 1
        self._new_ping.set()
        return super().ping_event()

    async def _valid_events(
        self,
        *,
        produce_last: bool,
    ) -> AsyncIterator[SSEvent[int]]:
        yield SSEvent(1)
        await self._wait_for_pings(1)  # one ping
        yield SSEvent(2)
        await self._wait_for_pings(3)  # two more pings
        if produce_last:
            yield SSEvent(3)

    async def _wait_for_pings(self, count: int) -> None:
        while self._pings < count:
            self._new_ping.clear()
            await self._new_ping.wait()


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
