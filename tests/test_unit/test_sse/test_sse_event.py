from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.http import HttpRequest

from dmr.cookies import CookieSpec, NewCookie
from dmr.headers import HeaderSpec
from dmr.metadata import ResponseSpec
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
from dmr.test import DMRAsyncRequestFactory

if TYPE_CHECKING:
    from tests.test_sse.conftest import GetStreamingContent


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield SSEvent(1, event='first', id=100, retry=5, comment='multi\nline\n')
    yield SSEvent(b'second', event=None, retry=None)
    yield SSEvent(b'third', retry=1, id=10)


@validation(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_valid_events(PydanticSerializer, renderer))


@pytest.mark.asyncio
async def test_all_sse_events_props(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b': multi\r\n'
        b': line\r\n'
        b': \r\n'
        b'id: 100\r\n'
        b'event: first\r\n'
        b'data: 1\r\n'
        b'retry: 5\r\n'
        b'\r\n'
        b'data: second\r\n'
        b'\r\n'
        b'id: 10\r\n'
        b'data: third\r\n'
        b'retry: 1\r\n'
        b'\r\n'
    )


async def _simple_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield b'simple'


@validation(
    PydanticSerializer,
    response_spec=ResponseSpec(
        SSEData,
        status_code=HTTPStatus.OK,
        headers={
            'Cache-Control': HeaderSpec(),
            'Connection': HeaderSpec(),
            'X-Accel-Buffering': HeaderSpec(),
            'X-Test': HeaderSpec(),
        },
        cookies={
            'session_id': CookieSpec(path='/sess'),
        },
    ),
)
async def _sse_with_headers_and_cookies(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(
        _simple_events(PydanticSerializer, renderer),
        headers={'X-Test': 'secret'},
        cookies={'session_id': NewCookie(value='cook', path='/sess')},
    )


@pytest.mark.asyncio
async def test_sse_with_headers_and_cookies(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _sse_with_headers_and_cookies.as_view()(request),
    )

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'X-Test': 'secret',
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert response.cookies.output() == (
        'Set-Cookie: session_id=cook; Path=/sess; SameSite=lax'
    )
    assert await get_streaming_content(response) == b'data: simple\r\n\r\n'
