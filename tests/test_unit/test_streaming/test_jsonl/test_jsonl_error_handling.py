from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pytest
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.jsonl import Json, JsonLinesController
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _JsonLinesEvents(JsonLinesController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[Json]:
        return self._valid_events()

    @override
    async def handle_event_error(self, exc: Exception) -> Any:
        if isinstance(exc, ZeroDivisionError):  # pragma: no branch
            return 'zero divizion'
        return await super().handle_event_error(exc)  # pragma: no cover

    async def _valid_events(self) -> AsyncIterator[Json]:
        yield 1
        # Error here:
        yield 1 / 0  # noqa: WPS344
        # Won't be sent:
        yield 2  # pragma: no cover


@pytest.mark.asyncio
async def test_jsonl_custom_error_handling(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we can customize the error handling in events."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_JsonLinesEvents.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == b'1\n"zero divizion"\n'
