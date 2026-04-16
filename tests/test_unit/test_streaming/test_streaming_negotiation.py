from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pytest
from typing_extensions import override

from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import default_renderer
from dmr.streaming import StreamingController, StreamingResponse
from dmr.streaming.jsonl.renderer import JsonLinesRenderer
from dmr.streaming.jsonl.validation import JsonLinesStreamingValidator
from dmr.streaming.renderer import StreamingRenderer
from dmr.streaming.sse import SSEvent
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.sse.validation import SSEStreamingValidator
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _ClassBasedStreaming(StreamingController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[Any]]:
        return self._valid_events()

    @classmethod
    @override
    def streaming_renderers(
        cls,
        serializer: type[PydanticSerializer],
    ) -> list[StreamingRenderer]:
        return [
            SSERenderer(
                serializer,
                default_renderer,
                SSEStreamingValidator,
            ),
            JsonLinesRenderer(
                serializer,
                default_renderer,
                JsonLinesStreamingValidator,
            ),
        ]

    async def _valid_events(self) -> AsyncIterator[SSEvent[Any]]:
        yield SSEvent({'a': 1})
        yield SSEvent(['b', 2])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('accept', 'expected_data'),
    [
        (
            ContentType.event_stream,
            b'data: {"a":1}\r\n\r\ndata: ["b",2]\r\n\r\n',
        ),
        (
            ContentType.jsonl,
            (
                b'{"data":{"a":1},"event":null,"id":null,'
                b'"retry":null,"comment":null}\n'
                b'{"data":["b",2],"event":null,"id":null,'
                b'"retry":null,"comment":null}\n'
            ),
        ),
    ],
)
async def test_valid_sse_different_methods(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    accept: ContentType,
    expected_data: bytes,
) -> None:
    """Ensures that we can negotiate streaming response types."""
    metadata = _ClassBasedStreaming.api_endpoints['GET'].metadata
    assert set(metadata.parsers) == {'application/json'}
    assert set(metadata.renderers) == {
        'application/json',
        'application/jsonl',
        'text/event-stream',
    }

    if isinstance(default_renderer, JsonRenderer):  # pragma: no cover
        pytest.skip(reason='JsonRenderer cannot render dataclasses')

    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Accept': f'{accept!s}, application/json'},
    )

    response = await dmr_async_rf.wrap(_ClassBasedStreaming.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': str(accept),
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == expected_data
