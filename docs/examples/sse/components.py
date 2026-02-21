from collections.abc import AsyncIterator

import msgspec
from django.http import HttpRequest

from dmr.components import Headers
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.sse import SSEContext, SSEData, SSEResponse, sse


class HeaderModel(msgspec.Struct):
    last_event_id: int | None = msgspec.field(
        default=None,
        name='Last-Event-ID',
    )


async def produce_user_events(
    request_headers: HeaderModel,
) -> AsyncIterator[SSEData]:
    if request_headers.last_event_id:
        yield f'starting from {request_headers.last_event_id}'.encode()
    else:
        yield b'starting from scratch'


@sse(MsgspecSerializer, headers=Headers[HeaderModel])
async def user_events(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext[None, None, HeaderModel],
) -> SSEResponse:
    return SSEResponse(produce_user_events(context.parsed_headers))


# run: {"controller": "user_events", "method": "get"}  # noqa: ERA001
# run: {"controller": "user_events", "method": "get", "headers": {"Last-Event-ID": 5}}  # noqa: ERA001, E501
# run: {"controller": "user_events", "method": "get", "headers": {"Last-Event-ID": "abc"}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
