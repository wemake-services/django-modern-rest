from typing import TYPE_CHECKING, ClassVar, Literal

from typing_extensions import override

from dmr.parsers import _NoOpParser  # pyright: ignore[reportPrivateUsage]
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.validation import StreamingValidator


class StreamingRenderer(Renderer):
    """
    Base class for all streaming responses.

    It is different from the regular :class:`~dmr.renderers.Renderer`
    in several ways:

    1. We need to initialize this renderer with a subrenderer,
       which will render the individual events itself
    2. Serializer is needed to serialize events
    3. Validator is needed to optionally validate events

    """

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
