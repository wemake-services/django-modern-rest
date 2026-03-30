from collections.abc import AsyncIterator
from typing import Any

from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming.jsonl import Json, JsonLinesController


class NumberEventsController(JsonLinesController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[Json]:
        return self._valid_events()

    @override
    async def handle_event_error(self, exc: Exception) -> Any:
        if isinstance(exc, ZeroDivisionError):
            return {'error': 'zero divizion'}
        return await super().handle_event_error(exc)

    async def _valid_events(self) -> AsyncIterator[Json]:
        yield 1
        # Error here:
        yield 1 / 0  # noqa: WPS344
        # Won't be sent:
        yield 2


# run: {"controller": "NumberEventsController", "method": "get"}  # noqa: ERA001
