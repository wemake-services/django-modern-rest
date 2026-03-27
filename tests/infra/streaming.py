import io

from dmr.streaming.stream import StreamingResponse


async def get_streaming_content(response: StreamingResponse) -> bytes:
    """Iterate over all items in a streaming response and return all bytes."""
    buffer = io.BytesIO()
    async for chunk in response:  # type: ignore[attr-defined]
        buffer.write(chunk)
    return buffer.getvalue()
