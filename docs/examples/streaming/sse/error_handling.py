from collections.abc import AsyncIterator
from typing import Any

from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming.sse import SSEController, SSEvent


class NumberEventsController(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[float]]:
        return self._valid_events()

    @override
    async def handle_event_error(self, exc: Exception) -> Any:
        if isinstance(exc, ZeroDivisionError):
            return SSEvent(b'zero divizion', event='error', serialize=False)
        return await super().handle_event_error(exc)

    async def _valid_events(self) -> AsyncIterator[SSEvent[float]]:
        yield SSEvent(1)
        # Error here:
        yield SSEvent(1 / 0)  # noqa: WPS344
        # Won't be sent:
        yield SSEvent(2)


# run: {"controller": "NumberEventsController", "method": "get"}  # noqa: ERA001
