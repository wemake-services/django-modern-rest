from collections.abc import AsyncIterator
from typing import Any

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.sse import (
    SSECloseConnectionError,
    SSEContext,
    SSEResponse,
    SSEvent,
    sse,
)


async def produce_user_events() -> AsyncIterator[SSEvent[bytes]]:
    message: Any
    for message in ('first', ['invalid', 'message', 'type']):
        try:
            yield SSEvent(message.encode('utf8'), serialize=False)
        except Exception:
            yield SSEvent(
                b'encountered invalid message',
                event='error',
                serialize=False,
            )
            raise SSECloseConnectionError from None


@sse(MsgspecSerializer)
async def user_events(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[bytes]]:
    return SSEResponse(produce_user_events())


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
