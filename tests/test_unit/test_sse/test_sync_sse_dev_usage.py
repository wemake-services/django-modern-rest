import asyncio
import io
from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest
from asgiref.sync import async_to_sync
from django.conf import LazySettings
from django.http import HttpRequest

from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.sse import (
    SSECloseConnectionError,
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
    sse,
)
from dmr.test import DMRRequestFactory


async def _valid_events() -> AsyncIterator[SSEData]:
    yield SSEvent(b'event')
    await asyncio.sleep(0.1)  # simulate work
    yield b'second'
    await asyncio.sleep(0.1)
    yield 3


@sse(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_valid_events())


def _get_sync_content(response: SSEStreamingResponse) -> bytes:
    buffer = io.BytesIO()
    for chunk in response:
        buffer.write(chunk)
    return buffer.getvalue()


def test_sync_sse_dev(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = True
    request = dmr_rf.get('/whatever/')

    response: SSEStreamingResponse = async_to_sync(
        _valid_sse.as_view(),  # type: ignore[arg-type]
    )(request)

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert not response.closed
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
    }
    assert _get_sync_content(response) == (
        b'data: event\r\n\r\ndata: second\r\n\r\ndata: 3\r\n\r\n'
    )
    assert not response.closed


def test_sync_sse_prod(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = False
    request = dmr_rf.get('/whatever/')

    response: SSEStreamingResponse = async_to_sync(
        _valid_sse.as_view(),  # type: ignore[arg-type]
    )(request)

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    with pytest.raises(
        RuntimeError,
        match='Do not use WSGI with SSE in production',
    ):
        _get_sync_content(response)


async def _events_with_close() -> AsyncIterator[SSEData]:
    yield SSEvent(b'event')
    yield SSEvent(b'second')
    raise SSECloseConnectionError


@sse(PydanticSerializer)
async def _sse_with_close(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_events_with_close())


def test_sync_sse_dev_with_close(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = True
    request = dmr_rf.get('/whatever/')

    response: SSEStreamingResponse = async_to_sync(
        _sse_with_close.as_view(),  # type: ignore[arg-type]
    )(request)

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert not response.closed
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
    }
    assert _get_sync_content(response) == (
        b'data: event\r\n\r\ndata: second\r\n\r\n'
    )
    assert response.closed
