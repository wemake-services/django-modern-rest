from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, TypeAlias

from typing_extensions import override

from dmr.streaming.validation import StreamingValidator, validate_event_type

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.jsonl import Json


JsonLinesPipeline: TypeAlias = Callable[
    ['Json', Any, type['BaseSerializer']],
    'Json',
]


class JsonLinesStreamingValidator(StreamingValidator):
    """Injects itself into the stream of json lines to validate the events."""

    __slots__ = ()

    @override
    def validation_pipeline(self) -> Iterable[JsonLinesPipeline]:
        """Validate the event type and the event payload."""
        return (
            # Order is important:
            validate_event_type,
        )
