import dataclasses
from collections.abc import AsyncIterator

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.streaming.jsonl import JsonLinesController


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


class UserEventsController(JsonLinesController[MsgspecSerializer]):
    async def get(self) -> AsyncIterator[_User]:
        return self.produce_user_events()

    async def produce_user_events(self) -> AsyncIterator[_User]:
        # You can send any complex data that can be serialized
        # by the controller's serializer:
        yield _User(email='first@example.com')
        yield _User(email='second@example.com')


# run: {"controller": "UserEventsController", "method": "get", "url": "/api/user/events/"}  # noqa: ERA001, E501
# openapi: {"controller": "UserEventsController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
