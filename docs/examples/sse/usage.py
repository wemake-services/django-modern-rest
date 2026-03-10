import dataclasses
from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


async def produce_user_events() -> AsyncIterator[SSEvent[_User]]:
    # You can send complex data, including json.
    # All SSEvent fields can be customized:
    yield SSEvent(
        _User(email='first@example.com'),
        event='user',
    )


@sse(MsgspecSerializer)
async def user_events(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[_User]]:
    return SSEResponse(produce_user_events())


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
