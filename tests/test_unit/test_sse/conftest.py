import io
from collections.abc import Awaitable, Callable
from typing import TypeAlias

import pytest

from dmr.sse import SSEStreamingResponse

GetStreamingContent: TypeAlias = Callable[
    [SSEStreamingResponse],
    Awaitable[bytes],
]


@pytest.fixture
def get_streaming_content() -> GetStreamingContent:
    """Iterate over all items in a streaming response and return all bytes."""

    async def factory(response: SSEStreamingResponse) -> bytes:
        buffer = io.BytesIO()
        async for chunk in response:
            buffer.write(chunk)
        return buffer.getvalue()

    return factory
