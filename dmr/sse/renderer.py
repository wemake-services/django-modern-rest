import re
from collections.abc import Callable
from io import BytesIO
from typing import TYPE_CHECKING, Any, Final

from typing_extensions import override

from dmr.exceptions import EndpointMetadataError
from dmr.parsers import (
    _NoOpParser,  # pyright: ignore[reportPrivateUsage]
)
from dmr.renderers import Renderer
from dmr.sse.metadata import SSEvent

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer

_DEFAULT_SEPARATOR: Final = b'\r\n'
_LINE_BREAK_RE: Final = re.compile(rb'\r\n|\r|\n')


class SSERenderer(Renderer):
    """
    Renders response as a stream of SSE.

    Uses sub-renderer to render events' data into the correct format.
    """

    __slots__ = (
        '_encoding',
        '_linebreak',
        '_regular_renderer',
        '_sep',
        '_serializer',
    )

    content_type = 'text/event-stream'

    def __init__(
        self,
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        *,
        sep: bytes = _DEFAULT_SEPARATOR,
        encoding: str = 'utf-8',
        linebreak: re.Pattern[bytes] = _LINE_BREAK_RE,
    ) -> None:
        """
        Initialize the renderer.

        Arguments:
            serializer: Serializer type to use for the SSE event internal data.
            regular_renderer: Renderer for the SSE event internal data.
            sep: Line and events separator.
            encoding: Encoding to convert string data into bytes.
            linebreak: How to process new lines in event's data.

        """
        self._serializer = serializer
        self._regular_renderer = regular_renderer
        self._sep = sep
        self._encoding = encoding
        self._linebreak = linebreak

    @override
    def render(  # noqa: C901, WPS213
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """Render a single event in the SSE chain of events."""
        if not isinstance(to_serialize, SSEvent):
            raise EndpointMetadataError(
                'SSERenderer can only render SSEvent instances, '
                f'got {type(to_serialize)}',
            )

        # We use BytesIO, because our json renderer returns `bytes`.
        # We don't want to convert it to string to convert it to bytes again.
        # Payload will always be preset,
        # while other metadata will frequently be missing.
        buffer = BytesIO()

        if to_serialize.comment is not None:
            for chunk in self._linebreak.split(
                to_serialize.comment.encode(self._encoding),
            ):
                buffer.write(b': ')
                buffer.write(chunk)
                buffer.write(self._sep)  # noqa: WPS204

        if to_serialize.id is not None:
            buffer.write(b'id: ')
            buffer.write(
                self._linebreak.sub(
                    b'',
                    str(to_serialize.id).encode(self._encoding),
                ),
            )
            buffer.write(self._sep)

        if to_serialize.event is not None:
            buffer.write(b'event: ')
            buffer.write(
                self._linebreak.sub(
                    b'',
                    to_serialize.event.encode(self._encoding),
                ),
            )
            buffer.write(self._sep)

        if to_serialize.data is not None:
            payload = (
                self._serializer.serialize(
                    to_serialize.data,
                    renderer=self._regular_renderer,
                )
                if to_serialize.serialize
                else to_serialize.data
            )
            for chunk in self._linebreak.split(payload):
                buffer.write(b'data: ')
                buffer.write(chunk)
                buffer.write(self._sep)

        if to_serialize.retry is not None:
            buffer.write(b'retry: ')
            buffer.write(str(to_serialize.retry).encode(self._encoding))
            buffer.write(self._sep)

        buffer.write(self._sep)
        return buffer.getvalue()

    @property
    @override
    def validation_parser(self) -> _NoOpParser:
        return _NoOpParser(self.content_type)
