from collections.abc import AsyncIterator, Callable
from http import HTTPStatus
from typing import Any, Final, TypeAlias

import pydantic
import pytest

from dmr.exceptions import ValidationError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.streaming.sse.validation import check_event_field
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

_Serializers: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializers] = [
    PydanticSerializer,
]

MsgspecSerializer: type[BaseSerializer] | None
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    MsgspecSerializer = None
else:  # pragma: no cover
    assert MsgspecSerializer is not None
    serializers.append(MsgspecSerializer)


_WRONG_CHARS: Final = ('\x00', '\n', '\r')


class _CustomEvent(pydantic.BaseModel):
    """Custom event type, it only respects the ``SSE`` protocol."""

    data: int
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    @property
    def should_serialize_data(self) -> bool:
        return True


_EventFactory: TypeAlias = Callable[[str], _CustomEvent]


def _custom_event_with_id(event_field: str) -> _CustomEvent:
    return _CustomEvent(data=1, id=event_field)


def _custom_event_with_event(event_field: str) -> _CustomEvent:
    return _CustomEvent(data=1, event=event_field)


@pytest.mark.parametrize('char', _WRONG_CHARS)
@pytest.mark.parametrize('field_name', ['id', 'event'])
def test_check_event_field_wrong_chars(char: str, field_name: str) -> None:
    """Ensures that wrong chars are reported as validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        check_event_field(f'prefix{char}suffix', field_name=field_name)

    assert exc_info.value.payload[0].get('loc') == [field_name]
    assert exc_info.value.payload[0].get('type') == 'streaming'


@pytest.mark.parametrize('event_field', ['correct', 1, None, object()])
def test_check_event_field_correct(event_field: Any) -> None:
    """Ensures that correct fields and non-str fields are allowed."""
    check_event_field(event_field, field_name='id')


@pytest.mark.asyncio
@pytest.mark.parametrize('char', _WRONG_CHARS)
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_id_is_validated(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    char: str,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that wrong ``id`` produces an error event."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[int]]:
            yield SSEvent(1, id=f'wrong{char}id')
            yield SSEvent(2)

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    stream = await get_streaming_content(response)
    assert b'event: error\r\n' in stream
    assert b'"loc":["id"]' in stream
    # The stream is not closed, the next event is still sent:
    assert stream.endswith(b'data: 2\r\n\r\n')


@pytest.mark.asyncio
@pytest.mark.parametrize('char', _WRONG_CHARS)
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_event_is_validated(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    char: str,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that wrong ``event`` produces an error event."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[int]]:
            yield SSEvent(1, event=f'wrong{char}event')
            yield SSEvent(2)

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    stream = await get_streaming_content(response)
    assert b'event: error\r\n' in stream
    assert b'"loc":["event"]' in stream
    assert stream.endswith(b'data: 2\r\n\r\n')


@pytest.mark.asyncio
@pytest.mark.parametrize('char', _WRONG_CHARS)
@pytest.mark.parametrize(
    ('field_name', 'make_event'),
    [
        ('id', _custom_event_with_id),
        ('event', _custom_event_with_event),
    ],
)
async def test_custom_event_type_is_validated(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    char: str,
    field_name: str,
    make_event: _EventFactory,
) -> None:
    """Ensures that custom event types are validated the same way."""

    class _ClassBasedSSE(SSEController[PydanticSerializer]):
        async def get(self) -> AsyncIterator[_CustomEvent]:
            return self._events()

        async def _events(self) -> AsyncIterator[_CustomEvent]:
            yield make_event(f'wrong{char}value')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    stream = await get_streaming_content(response)
    assert b'event: error\r\n' in stream
    assert f'"loc":["{field_name}"]'.encode() in stream


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_chars_skipped_when_disabled(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that ``validate_events=False`` trusts the user's data."""

    class _ClassBasedSSE(
        SSEController[serializer],  # type: ignore[valid-type]
    ):
        validate_events = False

        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return self._events()

        async def _events(self) -> AsyncIterator[SSEvent[int]]:
            yield SSEvent(1, id='wrong\nid', event='wrong\nevent')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'id: wrong\nid\r\n'  # noqa: WPS342
        b'event: wrong\nevent\r\n'  # noqa: WPS342
        b'data: 1\r\n'
        b'\r\n'
    )


@pytest.mark.asyncio
async def test_custom_event_skipped_when_disabled(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that custom types are not validated when disabled either."""

    class _ClassBasedSSE(SSEController[PydanticSerializer]):
        validate_events = False

        async def get(self) -> AsyncIterator[_CustomEvent]:
            return self._events()

        async def _events(self) -> AsyncIterator[_CustomEvent]:
            yield _CustomEvent(data=1, id='wrong\nid', event='wrong\nevent')

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'id: wrong\nid\r\n'  # noqa: WPS342
        b'event: wrong\nevent\r\n'  # noqa: WPS342
        b'data: 1\r\n'
        b'\r\n'
    )
