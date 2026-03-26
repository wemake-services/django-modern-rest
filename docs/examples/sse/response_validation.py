from collections.abc import AsyncIterator

from django.http import HttpRequest

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


async def events() -> AsyncIterator[SSEvent[str]]:
    yield SSEvent('example')


@sse(MsgspecSerializer)  # validate_responses is True by default
async def with_validation(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[str]]:
    return SSEResponse(events(), headers={'X-Example': 'value'})


@sse(MsgspecSerializer, validate_responses=False)
async def no_validation(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[str]]:
    return SSEResponse(events(), headers={'X-Example': 'value'})


# run: {"controller": "with_validation", "method": "get", "curl_args": ["-D", "-"], "assert-error-text": "x-example", "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "no_validation", "method": "get"}  # noqa: ERA001
