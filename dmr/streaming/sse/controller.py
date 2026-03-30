from typing import Any, ClassVar, TypeVar

from typing_extensions import override

from dmr.errors import ErrorType
from dmr.exceptions import ValidationError
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.settings import default_renderer
from dmr.streaming.controller import StreamingController
from dmr.streaming.renderer import StreamingRenderer
from dmr.streaming.sse.metadata import SSEvent
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.sse.validation import SSEStreamingValidator

_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)


class SSEController(StreamingController[_SerializerT_co]):
    """
    Controller for streaming Server Sent Events (SSE).

    .. danger::

        WSGI handers do not support streaming responses, including SSE,
        by default. You would need to use ASGI handler for streaming endpoints.

        We allow running SSE during ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with streaming.

    """

    streaming_ping_seconds = 15.0

    # Custom attributes:
    streaming_default_renderer: ClassVar[Renderer] = default_renderer
    """Default renderer for event ``body`` field."""

    streaming_validator_cls: ClassVar[type[SSEStreamingValidator]] = (
        SSEStreamingValidator
    )
    """Validator for events, only active when ``validate_events`` is set."""

    @override
    @classmethod
    def streaming_renderers(
        cls,
        serializer: type[_SerializerT_co],  # pyright: ignore[reportGeneralTypeIssues]
    ) -> list[StreamingRenderer]:
        return [
            SSERenderer(
                serializer,
                cls.streaming_default_renderer,
                cls.streaming_validator_cls,
            ),
        ]

    @override
    async def handle_event_error(self, exc: Exception) -> Any:
        """
        Handles errors that can happen while sending events.

        Return alternative event that will indicate what error has happened.
        By default does nothing and just reraises the exception.
        """
        if isinstance(exc, ValidationError):
            return SSEvent(
                self.format_error(exc, error_type=ErrorType.streaming),
                event='error',
            )
        return await super().handle_event_error(exc)

    @override
    def ping_event(self) -> Any | None:
        """Return a ping event to be generated if this streaming needs it."""
        return SSEvent(comment='ping')
