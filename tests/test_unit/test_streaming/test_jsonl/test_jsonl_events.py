from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest

from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.jsonl import Json, JsonLinesController
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _JsonLinesEvents(JsonLinesController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[Json]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[Json]:
        yield 1
        yield 1.0
        yield False
        yield None
        yield 'string'
        yield ['a\nb', True, {}]
        yield {'key': 'multi\r\nline', 'nested': {'prop': [1, 2]}}


@pytest.mark.asyncio
async def test_jsonl_all_events_render(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we can render all possible event types."""
    assert _JsonLinesEvents.streaming_ping_seconds is None

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_JsonLinesEvents.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'1\n'
        b'1.0\n'
        b'false\n'
        b'null\n'
        b'"string"\n'
        b'["a\\nb",true,{}]\n'  # noqa: WPS342
        b'{"key":"multi\\r\\nline","nested":{"prop":[1,2]}}\n'  # noqa: WPS342
    )
