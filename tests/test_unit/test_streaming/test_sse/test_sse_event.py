from collections.abc import AsyncIterator
from http import HTTPMethod, HTTPStatus
from typing import Any

import pytest

from dmr import modify, validate
from dmr.cookies import CookieSpec, NewCookie
from dmr.headers import HeaderSpec, NewHeader
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.streaming import (
    StreamingCloseError,
    StreamingResponse,
    streaming_response_spec,
)
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

MsgspecSerializer: type[BaseSerializer] | None
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    MsgspecSerializer = None


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    """Doc for tests."""

    @validate(
        streaming_response_spec(
            SSEvent[Any],
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        return self.to_stream(self._valid_events())

    async def post(self) -> AsyncIterator[SSEvent[Any]]:
        return self._valid_events()

    async def delete(self) -> AsyncIterator[SSEvent[Any]]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[SSEvent[Any]]:
        yield SSEvent(
            1,
            event='first',
            id=100,
            retry=5,
            comment='multi\nline\n',
        )
        yield SSEvent(b'third', retry=1, id=10, serialize=False)
        yield SSEvent({'user': 1})
        yield SSEvent(comment='ping')
        yield SSEvent(event='pong')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.DELETE,
    ],
)
async def test_all_sse_events_props(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that valid sse produces valid results."""
    assert _ClassBasedSSE.__name__ == '_ClassBasedSSE'
    assert _ClassBasedSSE.__qualname__ == '_ClassBasedSSE'
    assert _ClassBasedSSE.__module__ == test_all_sse_events_props.__module__
    assert _ClassBasedSSE.__doc__ == 'Doc for tests.'

    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
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


class _SSEWithHeadersAndCookies(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
            headers={'X-Test': HeaderSpec()},
            cookies={'session_id': CookieSpec(path='/sess')},
        ),
    )
    async def get(self) -> StreamingResponse:
        return self.to_stream(
            self._events(),
            headers={'X-Test': 'secret'},
            cookies={'session_id': NewCookie(value='cook', path='/sess')},
        )

    @modify(
        headers={'X-Test': NewHeader(value='secret')},
        cookies={'session_id': NewCookie(value='cook', path='/sess')},
    )
    async def post(self) -> AsyncIterator[SSEvent[bytes]]:
        return self._events()

    async def _events(self) -> AsyncIterator[SSEvent[bytes]]:
        yield SSEvent(b'simple', serialize=False)


@pytest.mark.asyncio
@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
async def test_sse_with_headers_and_cookies(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(
        _SSEWithHeadersAndCookies.as_view()(request),
    )

    assert isinstance(response, StreamingResponse)
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


class _SSEWithClose(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            SSEvent[int],
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        return self.to_stream(self._events())

    @modify(description='test')
    async def post(self) -> AsyncIterator[SSEvent[int]]:
        return self._events()

    async def put(self) -> AsyncIterator[SSEvent[int]]:
        return self._events()

    async def _events(self) -> AsyncIterator[SSEvent[int]]:
        yield SSEvent(1, event='first')
        raise StreamingCloseError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method',
    [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT],
)
async def test_sse_close_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that valid sse can raise close error."""
    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(_SSEWithClose.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'event: first\r\ndata: 1\r\n\r\n'
    )


class _SSEWithNewlines(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[Any]]:
        return self._events()

    async def _events(self) -> AsyncIterator[SSEvent[Any]]:
        yield SSEvent({'newline in key\n': 1})
        yield SSEvent(['list item with\nnewline'])
        yield SSEvent('new\r\nline in str')
        yield SSEvent(b'new\r\nline in bytes', serialize=False)


@pytest.mark.asyncio
async def test_sse_newlines_in_data(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that newlines in different data."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_SSEWithNewlines.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'data: {"newline in key\\n":1}\r\n'  # noqa: WPS342
        b'\r\n'
        b'data: ["list item with\\nnewline"]\r\n'  # noqa: WPS342
        b'\r\n'
        b'data: "new\\r\\nline in str"\r\n'  # noqa: WPS342
        b'\r\n'
        b'data: new\r\n'
        b'data: line in bytes\r\n'
        b'\r\n'
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
