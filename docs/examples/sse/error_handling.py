import dataclasses
from collections.abc import AsyncIterator
from typing import Any

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.sse import (
    SSECloseConnectionError,
    SSEContext,
    SSEData,
    SSEResponse,
    SSEvent,
    sse,
)


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


async def produce_user_events() -> AsyncIterator[SSEData]:
    message: Any
    for message in ('first', ['invalid', 'message', 'type']):
        try:
            yield message.encode('utf8')
        except Exception:
            yield SSEvent(b'encountered invalid message', event='error')
            raise SSECloseConnectionError from None


@sse(MsgspecSerializer)
async def user_events(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(produce_user_events())


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
