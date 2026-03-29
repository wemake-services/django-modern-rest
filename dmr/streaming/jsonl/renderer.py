from collections.abc import Callable
from io import BytesIO
from typing import TYPE_CHECKING, Any, Final

from typing_extensions import override

from dmr.negotiation import ContentType
from dmr.renderers import Renderer
from dmr.streaming.renderer import StreamingRenderer

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.validation import StreamingValidator

_DEFAULT_SEPARATOR: Final = b'\n'


class JsonLinesRenderer(StreamingRenderer):
    """
    Renders response as a stream of json liens.

    Uses sub-renderer to render events' data into the correct format.
    """

    __slots__ = (
        '_encoding',
        '_linebreak',
        '_sep',
    )

    content_type = ContentType.jsonl

    def __init__(  # noqa: WPS211
        self,
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        streaming_validator_cls: type['StreamingValidator'],
        *,
        sep: bytes = _DEFAULT_SEPARATOR,
    ) -> None:
        """
        Initialize the renderer.

        Arguments:
            serializer: Serializer type to use for the SSE event internal data.
            regular_renderer: Renderer for the SSE event internal data.
            streaming_validator_cls: Stream validator class.
            sep: Line and events separator.

        """
        super().__init__(serializer, regular_renderer, streaming_validator_cls)
        self._sep = sep

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """Render a single event in the json lines stream of events."""
        buffer = BytesIO()
        buffer.write(
            self._serializer.serialize(
                to_serialize,
                renderer=self._regular_renderer,
            ),
        )
        buffer.write(self._sep)
        return buffer.getvalue()
