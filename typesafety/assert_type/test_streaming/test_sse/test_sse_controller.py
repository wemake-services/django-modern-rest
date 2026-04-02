from collections.abc import AsyncIterator
from typing import Any

from dmr import validate
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.sse import SSEController, SSEvent


async def _valid_events() -> AsyncIterator[SSEvent[bytes]]:
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)


class _InvalidController(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        # Missing `self.to_stream()`
        return _valid_events()  # type: ignore[return-value]

    async def post(self) -> AsyncIterator[Any]:
        # Extra `self.to_stream()`
        return self.to_stream(_valid_events())  # type: ignore[return-value]
