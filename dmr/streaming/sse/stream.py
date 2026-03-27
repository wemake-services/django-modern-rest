from typing import Any

from typing_extensions import override

from dmr.errors import ErrorModel
from dmr.exceptions import ValidationError
from dmr.streaming.sse.metadata import SSEvent
from dmr.streaming.stream import StreamingResponse


class SSEStreamingResponse(StreamingResponse):
    @override
    def handle_event_error(
        self,
        event: Any,
        exc: Exception,
    ) -> Any:
        """
        Handles errors that can happen while sending events.

        Return alternative event that will indicate what error has happened.
        By default does nothing and just reraises the exception.
        """
        if isinstance(exc, ValidationError):
            return SSEvent(ErrorModel(detail=exc.payload), event='error')
        return super().handle_event_error(event, exc)
