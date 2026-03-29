import dataclasses
from collections.abc import AsyncIterator

from dmr import validate
from dmr.negotiation import ContentType
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.jsonl import JsonLinesController


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


class UserEventsController(JsonLinesController[MsgspecSerializer]):
    @validate(
        streaming_response_spec(
            _User,
            content_type=ContentType.jsonl,
        ),
    )
    async def get(self) -> StreamingResponse:
        return self.to_stream(self.produce_user_events())

    async def produce_user_events(self) -> AsyncIterator[_User]:
        # You can send any complex data that can be serialized
        # by the controller's serializer:
        yield _User(email='first@example.com')
        yield _User(email='second@example.com')


# run: {"controller": "UserEventsController", "method": "get", "url": "/api/user/events/"}  # noqa: ERA001, E501
# openapi: {"controller": "UserEventsController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
