import io
from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest
from asgiref.sync import async_to_sync
from django.conf import LazySettings
from django.http import HttpRequest

from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
    validation,
)
from dmr.test import DMRRequestFactory


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield SSEvent(b'event')


@validation(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_valid_events(PydanticSerializer, renderer))


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
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
    }
    assert _get_sync_content(response) == (b'data: event\r\n\r\n')


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
        match='Do not use wsgi with SSE in production',
    ):
        _get_sync_content(response)
