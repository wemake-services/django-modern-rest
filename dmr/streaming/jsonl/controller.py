from typing import Any, ClassVar, TypeVar

from typing_extensions import override

from dmr.errors import ErrorType
from dmr.exceptions import ValidationError
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.settings import default_renderer
from dmr.streaming.controller import StreamingController
from dmr.streaming.jsonl.renderer import JsonLinesRenderer
from dmr.streaming.jsonl.validation import JsonLinesStreamingValidator
from dmr.streaming.renderer import StreamingRenderer

_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)


class JsonLinesController(StreamingController[_SerializerT_co]):
    """
    Controller for streaming json lines (JsonL).

    .. seealso::

        Json Lines standard: https://jsonlines.org

    .. danger::

        WSGI handers do not support streaming responses, including JsonLines,
        by default. You would need to use ASGI handler for streaming endpoints.

        We allow running streaming
        during ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with JsonLines.

    """

    streaming_default_renderer: ClassVar[Renderer] = default_renderer
    streaming_validator_cls: ClassVar[type[JsonLinesStreamingValidator]] = (
        JsonLinesStreamingValidator
    )

    @override
    @classmethod
    def streaming_renderers(
        cls,
        serializer: type[_SerializerT_co],  # pyright: ignore[reportGeneralTypeIssues]
    ) -> list[StreamingRenderer]:
        return [
            JsonLinesRenderer(
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
            return self.format_error(exc, error_type=ErrorType.streaming)
        return await super().handle_event_error(exc)
