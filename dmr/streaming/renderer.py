from typing import TYPE_CHECKING, ClassVar, Literal

from typing_extensions import override

from dmr.parsers import _NoOpParser  # pyright: ignore[reportPrivateUsage]
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


class StreamingRenderer(Renderer):
    streaming: ClassVar[Literal[True]] = True

    __slots__ = (
        '_regular_renderer',
        '_serializer',
    )

    def __init__(
        self,
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
    ) -> None:
        """
        Initialize the renderer.

        Arguments:
            serializer: Serializer type to use for the SSE event internal data.
            regular_renderer: Renderer for the SSE event internal data.

        """
        self._serializer = serializer
        self._regular_renderer = regular_renderer

    @property
    @override
    def validation_parser(self) -> _NoOpParser:
        return _NoOpParser(self.content_type)
