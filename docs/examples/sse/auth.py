from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.security.django_session import DjangoSessionAsyncAuth
from dmr.sse import SSEContext, SSEData, SSEResponse, sse


async def produce_user_events(username: str) -> AsyncIterator[SSEData]:
    yield f'hello {username}'.encode()


@sse(MsgspecSerializer, auth=[DjangoSessionAsyncAuth()])
async def user_events(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    user = await request.auser()
    return SSEResponse(produce_user_events(user.get_username()))
