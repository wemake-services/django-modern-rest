import dataclasses
from collections.abc import AsyncIterator

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.streaming.sse import SSEController, SSEvent


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


class UserEventsController(SSEController[MsgspecSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[_User]]:
        return self.produce_user_events()

    async def produce_user_events(self) -> AsyncIterator[SSEvent[_User]]:
        # You can send any complex data that can be serialized
        # by the controller's serializer,
        # all SSEvent fields can be customized:
        yield SSEvent(
            _User(email='first@example.com'),
            event='user',
        )
        yield SSEvent(
            _User(email='second@example.com'),
            event='user',
        )


# run: {"controller": "UserEventsController", "method": "get", "url": "/api/user/events/"}  # noqa: ERA001, E501
# openapi: {"controller": "UserEventsController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
