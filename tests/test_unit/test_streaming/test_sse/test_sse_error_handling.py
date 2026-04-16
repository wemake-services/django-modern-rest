from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pytest
from typing_extensions import override

from dmr.exceptions import DataRenderingError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[float]]:
        return self._valid_events()

    @override
    async def handle_event_error(self, exc: Exception) -> Any:
        if isinstance(exc, ZeroDivisionError):  # pragma: no branch
            return SSEvent(b'zero divizion', event='error', serialize=False)
        return await super().handle_event_error(exc)  # pragma: no cover

    async def _valid_events(self) -> AsyncIterator[SSEvent[float]]:
        yield SSEvent(1)
        # Error here:
        yield SSEvent(1 / 0)  # noqa: WPS344
        # Won't be sent:
        yield SSEvent(2)  # pragma: no cover


@pytest.mark.asyncio
async def test_sse_custom_error_handling(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we can customize the error handling in events."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'data: 1\r\n\r\nevent: error\r\ndata: zero divizion\r\n\r\n'
    )


class _CustomData:
    """Unserializable."""


class _CustomType:
    """Unserializable."""

    data = _CustomData()
    event: Any = None
    id: Any = None
    comment: Any = None
    retry: Any = None
    should_serialize_data = True


class _SSECustomType(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[Any]:
        return self._invalid_events()

    async def _invalid_events(self) -> AsyncIterator[Any]:
        yield _CustomType()


@pytest.mark.asyncio
async def test_sse_event_serialization(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we raise on unserializable event types."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_SSECustomType.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(DataRenderingError, match='_CustomData'):
        await get_streaming_content(response)
