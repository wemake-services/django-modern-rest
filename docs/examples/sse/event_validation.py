from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.sse import SSEContext, SSEData, SSEResponse, sse


async def produce_events() -> AsyncIterator[SSEData]:
    yield ['not', 'valid', 'event', 'data']  # type: ignore[misc]


@sse(MsgspecSerializer, validate_events=False)
async def user_events(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(produce_events())


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
