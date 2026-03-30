from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing
from typing import Annotated

from typing_extensions import override

from dmr.negotiation import ContentType, conditional_type
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import default_renderer
from dmr.streaming import StreamingController
from dmr.streaming.jsonl import Json
from dmr.streaming.jsonl.renderer import JsonLinesRenderer
from dmr.streaming.jsonl.validation import JsonLinesStreamingValidator
from dmr.streaming.renderer import StreamingRenderer
from dmr.streaming.sse import SSEvent
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.sse.validation import SSEStreamingValidator


class EventStreaming(StreamingController[PydanticSerializer]):
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

    async def get(
        self,
    ) -> AsyncIterator[
        Annotated[
            SSEvent[Json] | Json,
            conditional_type({
                ContentType.jsonl: Json,
                ContentType.event_stream: SSEvent[Json],
            }),
        ],
    ]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[SSEvent[Json] | Json]:
        async with aclosing(self._source()) as source:
            async for event in source:
                if self.request.accepts(ContentType.event_stream):
                    yield SSEvent(event)
                else:
                    yield event

    async def _source(self) -> AsyncGenerator[Json]:
        yield {'a': 1}
        yield ['b', 2]


# run: {"controller": "EventStreaming", "method": "get", "headers": {"Accept": "application/jsonl, application/json"}, "url": "/api/user/events/"}  # noqa: ERA001, E501
# run: {"controller": "EventStreaming", "method": "get", "headers": {"Accept": "text/event-stream, application/json"}, "url": "/api/user/events/"}  # noqa: ERA001, E501
# openapi: {"controller": "EventStreaming", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
