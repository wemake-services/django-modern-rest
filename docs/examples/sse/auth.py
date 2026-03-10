from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.django_session import DjangoSessionAsyncAuth
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


async def produce_user_events(username: str) -> AsyncIterator[SSEvent[str]]:
    yield SSEvent(f'hello {username}')


@sse(MsgspecSerializer, auth=[DjangoSessionAsyncAuth()])
async def user_events(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[str]]:
    user = await request.auser()
    return SSEResponse(produce_user_events(user.get_username()))
