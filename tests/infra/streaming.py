import io

from dmr.sse import SSEStreamingResponse


async def get_streaming_content(response: SSEStreamingResponse) -> bytes:
    """Iterate over all items in a streaming response and return all bytes."""
    buffer = io.BytesIO()
    async for chunk in response:
        buffer.write(chunk)
    return buffer.getvalue()
