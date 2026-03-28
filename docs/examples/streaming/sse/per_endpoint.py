from collections.abc import AsyncIterator
from typing import Any

from dmr import modify
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.streaming.sse import SSEController, SSEvent


class UserEventsController(SSEController[MsgspecSerializer]):
    @modify(validate_events=False)
    async def get(self) -> AsyncIterator[SSEvent[int]]:
        return self.produce_user_events()

    async def produce_user_events(self) -> AsyncIterator[SSEvent[Any]]:
        yield SSEvent('not-an-int')


# run: {"controller": "UserEventsController", "method": "get", "url": "/api/user/events/"}  # noqa: ERA001, E501
