from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Final, TypeAlias, get_args

from typing_extensions import override

from dmr.exceptions import ValidationError
from dmr.streaming.validation import StreamingValidator, validate_event_type

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.sse.metadata import SSE


def validate_event_data(
    event: Any,
    model: Any,
    serializer: type['BaseSerializer'],
) -> Any:
    """Validates ``SSEvent.data`` to be of the given type arg."""
    from dmr.streaming.sse.metadata import SSEvent  # noqa: PLC0415

    if not isinstance(event, SSEvent):
        # Might be a custom type:
        return event

    type_args = get_args(model)
    if not type_args:
        # Might be a custom alias, or missing item:
        return event  # pyright: ignore[reportUnknownVariableType]

    try:
        serializer.from_python(
            event.data,  # pyright: ignore[reportUnknownMemberType]
            model=type_args[0],
            strict=True,
        )
    except serializer.validation_error as exc:
        raise ValidationError(
            serializer.serialize_validation_error(exc),
        ) from None
    return event  # pyright: ignore[reportUnknownVariableType]


SSEPipeline: TypeAlias = Callable[
    ['SSE', Any, type['BaseSerializer']],
    'SSE',
]


class SSEStreamingValidator(StreamingValidator):
    """Injects itself into the stream of SSE to validate the events."""

    __slots__ = ()

    @override
    def validation_pipeline(self) -> Iterable[SSEPipeline]:
        """Validate the event type and the event payload."""
        return (
            # Order is important:
            validate_event_type,
            validate_event_data,
        )


# Source:
# https://html.spec.whatwg.org/multipage/server-sent-events.html#the-last-event-id-header
_NULL_CHAR: Final = '\x00'
_LR: Final = '\r'
_NL: Final = '\n'


def check_event_field(event_field: Any, field_name: str) -> None:
    """Checks that event field does not contain wrong chars."""
    if isinstance(event_field, str):
        if _NULL_CHAR in event_field:
            raise ValueError(
                f'Event {field_name} must not contain null byte "\x00"',
            )
        if _LR in event_field or _NL in event_field:
            raise ValueError(f'Event {field_name} must not contain line breaks')
