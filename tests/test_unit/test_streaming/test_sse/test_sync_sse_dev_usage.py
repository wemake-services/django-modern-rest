import asyncio
import io
from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus

import pytest
from asgiref.sync import async_to_sync
from django.conf import LazySettings

from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingCloseError, StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRRequestFactory


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[str | bytes | int]]:
        return self._events()

    async def post(self) -> AsyncIterator[SSEvent[str | bytes | int]]:
        return self._events()

    async def _events(self) -> AsyncIterator[SSEvent[str | bytes | int]]:
        yield SSEvent('event')
        await asyncio.sleep(0.1)  # simulate work
        yield SSEvent(b'second', serialize=False)
        await asyncio.sleep(0.1)
        yield SSEvent(3)


def _get_sync_content(response: StreamingResponse) -> bytes:
    buffer = io.BytesIO()
    for chunk in response:
        buffer.write(chunk)
    return buffer.getvalue()


@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
def test_sync_sse_dev(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = True
    request = dmr_rf.generic(str(method), '/whatever/')

    response: StreamingResponse = async_to_sync(
        _ClassBasedSSE.as_view(),  # type: ignore[arg-type]
    )(request)

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert not response.closed
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
    }
    assert _get_sync_content(response) == (
        b'data: "event"\r\n\r\ndata: second\r\n\r\ndata: 3\r\n\r\n'
    )
    assert response.closed


@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
def test_sync_sse_prod(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = False
    request = dmr_rf.generic(str(method), '/whatever/')

    response: StreamingResponse = async_to_sync(
        _ClassBasedSSE.as_view(),  # type: ignore[arg-type]
    )(request)

    assert isinstance(response, StreamingResponse)
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
        match='Do not use WSGI with event streaming in production',
    ):
        _get_sync_content(response)


class _SyncClassBasedSSE(SSEController[PydanticSerializer]):
    def get(self) -> AsyncIterator[SSEvent[str]]:
        return self._events()

    async def _events(self) -> AsyncIterator[SSEvent[str]]:
        yield SSEvent('event')


def test_sync_sse_dev_from_sync_method(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = True
    request = dmr_rf.get('/whatever/')

    response = _SyncClassBasedSSE.as_view()(request)

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert not response.closed
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
    }
    assert _get_sync_content(response) == (b'data: "event"\r\n\r\n')
    assert response.closed


def test_sync_sse_prod_from_sync_method(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = False
    request = dmr_rf.get('/whatever/')

    response = _SyncClassBasedSSE.as_view()(request)

    assert isinstance(response, StreamingResponse)
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
        match='Do not use WSGI with event streaming in production',
    ):
        _get_sync_content(response)


class _SSEWithClose(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[str | bytes | int]]:
        yield SSEvent(b'event', serialize=False)
        yield SSEvent(b'second', serialize=False)
        raise StreamingCloseError


def test_sync_sse_dev_with_close(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that it is possible to iterate over response in sync mode."""
    settings.DEBUG = True
    request = dmr_rf.get('/whatever/')

    response = _SSEWithClose.as_view()(request)

    assert isinstance(response, StreamingResponse)
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
