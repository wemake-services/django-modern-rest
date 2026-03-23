from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpRequest

from dmr.cookies import CookieSpec, NewCookie
from dmr.headers import HeaderSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSECloseConnectionError,
    SSEContext,
    SSEResponse,
    SSEResponseSpec,
    SSEStreamingResponse,
    SSEvent,
    sse,
)
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

MsgspecSerializer: type[BaseSerializer] | None
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    MsgspecSerializer = None


async def _valid_events() -> AsyncIterator[SSEvent[Any]]:
    yield SSEvent(1, event='first', id=100, retry=5, comment='multi\nline\n')
    yield SSEvent(b'second', event=None, retry=None)
    yield SSEvent(b'third', retry=1, id=10, serialize=False)
    yield SSEvent({'user': 1})
    yield SSEvent(comment='ping')
    yield SSEvent(event='pong')


@sse(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[Any]]:
    """Doc for tests."""
    return SSEResponse(_valid_events())


@pytest.mark.asyncio
@pytest.mark.skipif(
    MsgspecSerializer is None,
    reason='regular json formats it differently',
)
async def test_all_sse_events_props(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    assert _valid_sse.__name__ == '_valid_sse'
    assert _valid_sse.__qualname__ == '_valid_sse'
    assert _valid_sse.__module__ == test_all_sse_events_props.__module__
    assert _valid_sse.__doc__ == 'Doc for tests.'

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
        b'data: "c2Vjb25k"\r\n'
        b'\r\n'
        b'id: 10\r\n'
        b'data: third\r\n'
        b'retry: 1\r\n'
        b'\r\n'
        b'data: {"user":1}\r\n'
        b'\r\n'
        b': ping\r\n'
        b'\r\n'
        b'event: pong\r\n'
        b'\r\n'
    )


async def _simple_events() -> AsyncIterator[SSEvent[bytes]]:
    yield SSEvent(b'simple', serialize=False)


@sse(
    PydanticSerializer,
    response_spec=SSEResponseSpec(
        SSEvent[bytes],
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
    context: SSEContext,
) -> SSEResponse[SSEvent[bytes]]:
    return SSEResponse(
        _simple_events(),
        headers={'X-Test': 'secret'},
        cookies={'session_id': NewCookie(value='cook', path='/sess')},
    )


@pytest.mark.asyncio
async def test_sse_with_headers_and_cookies(
    dmr_async_rf: DMRAsyncRequestFactory,
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


async def _events_with_close() -> AsyncIterator[SSEvent[int]]:
    yield SSEvent(1, event='first')
    raise SSECloseConnectionError


@sse(PydanticSerializer)
async def _sse_with_close(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[int]]:
    return SSEResponse(_events_with_close())


@pytest.mark.asyncio
async def test_sse_close_error(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse can raise close error."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_sse_with_close.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'event: first\r\ndata: 1\r\n\r\n'
    )


def test_event_model_validation() -> None:
    """Ensure that validation for event works."""
    with pytest.raises(ValueError, match='At least one event field'):
        SSEvent()  # type: ignore[call-overload]

    with pytest.raises(ValueError, match='data must be an instance of "bytes"'):
        SSEvent({}, serialize=False)  # type: ignore[call-overload]


@pytest.mark.parametrize(
    'char',
    [
        '\x00',
        '\n',
        '\r',
    ],
)
def test_wrong_chars(char: str) -> None:
    """Ensures that wrong chars can't be used in some fields."""
    with pytest.raises(ValueError, match='Event'):
        SSEvent({}, id=char)
    with pytest.raises(ValueError, match='Event'):
        SSEvent({}, event=char)
