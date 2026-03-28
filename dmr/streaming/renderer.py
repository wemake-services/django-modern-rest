from typing import TYPE_CHECKING, ClassVar, Literal

from typing_extensions import override

from dmr.parsers import _NoOpParser  # pyright: ignore[reportPrivateUsage]
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.validation import StreamingValidator


class StreamingRenderer(Renderer):
    streaming: ClassVar[Literal[True]] = True  # pyright: ignore[reportIncompatibleVariableOverride]

    __slots__ = (
        '_regular_renderer',
        '_serializer',
        'streaming_validator_cls',
    )

    def __init__(
        self,
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        streaming_validator_cls: type['StreamingValidator'],
    ) -> None:
        """
        Initialize the renderer.

        Arguments:
            serializer: Serializer type to use for the SSE event internal data.
            regular_renderer: Renderer for the SSE event internal data.
            streaming_validator_cls: Type to validate stream events.

        """
        self._serializer = serializer
        self._regular_renderer = regular_renderer
        self.streaming_validator_cls = streaming_validator_cls

    @property
    @override
    def validation_parser(self) -> _NoOpParser:
        raise NotImplementedError('StreamingRenderer must not return a parser')
