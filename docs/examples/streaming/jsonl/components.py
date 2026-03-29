from collections.abc import AsyncIterator

import msgspec

from dmr.components import Headers
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.streaming.jsonl import Json, JsonLinesController


class HeaderModel(msgspec.Struct):
    last_event_id: int | None = msgspec.field(
        default=None,
        name='Last-Event-ID',
    )


class UserEventsController(JsonLinesController[MsgspecSerializer]):
    def get(
        self,
        parsed_headers: Headers[HeaderModel],
    ) -> AsyncIterator[Json]:
        return self.produce_user_events(parsed_headers)

    async def produce_user_events(
        self,
        parsed_headers: HeaderModel,
    ) -> AsyncIterator[Json]:
        if parsed_headers.last_event_id is None:
            yield 'starting from scratch'
        else:
            yield f'starting from {parsed_headers.last_event_id}'


# run: {"controller": "UserEventsController", "method": "get"}  # noqa: ERA001
# run: {"controller": "UserEventsController", "method": "get", "headers": {"Last-Event-ID": 5}}  # noqa: ERA001, E501
# run: {"controller": "UserEventsController", "method": "get", "headers": {"Last-Event-ID": "abc"}, "curl_args": ["-D", "-"], "assert-error-text": "last_event_id", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "UserEventsController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
