from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


async def produce_events() -> AsyncIterator[SSEvent[str]]:
    yield SSEvent('skipped event validation')


@sse(MsgspecSerializer, validate_events=False)
async def user_events(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[int]]:
    return SSEResponse(produce_events())  # type: ignore[arg-type]


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
