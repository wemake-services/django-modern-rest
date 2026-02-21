import dataclasses
from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.sse import SSEContext, SSEData, SSEResponse, SSEvent, sse


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


async def produce_user_events(
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    # You can send complex data, including json.
    # All SSEvent fields can be customized:
    yield SSEvent(
        MsgspecSerializer.serialize(
            _User(email='first@example.com'),
            renderer=renderer,
        ),
        event='user',
        comment='authenticated as',
    )

    # Or you can yield regular bytes:
    yield b'regular bytes'
    yield b'multiline\nbyte\nstring'


@sse(MsgspecSerializer)
async def user_events(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(produce_user_events(renderer))


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
