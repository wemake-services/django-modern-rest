from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Final, TypeAlias, get_args

from typing_extensions import override

from dmr.errors import ErrorDetail, ErrorType
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


# Source:
# https://html.spec.whatwg.org/multipage/server-sent-events.html#the-last-event-id-header
_NULL_CHAR: Final = '\x00'
_LR: Final = '\r'
_NL: Final = '\n'


def check_event_field(event_field: Any, field_name: str) -> None:
    """
    Checks that event field does not contain wrong chars.

    Only ``str`` fields are checked, any other type is left as is.

    Raises:
        ValidationError: When the field contains a null byte or a line break.

    """
    if not isinstance(event_field, str):
        return
    if _NULL_CHAR in event_field:
        raise ValidationError([
            ErrorDetail(
                msg=f'Event {field_name} must not contain null byte "\\x00"',
                type=ErrorType.streaming,
                loc=[field_name],
            ),
        ])
    if _LR in event_field or _NL in event_field:
        raise ValidationError([
            ErrorDetail(
                msg=f'Event {field_name} must not contain line breaks',
                type=ErrorType.streaming,
                loc=[field_name],
            ),
        ])


def validate_event_fields(
    event: 'SSE',
    model: Any,
    serializer: type['BaseSerializer'],
) -> 'SSE':
    """
    Validates that ``id`` and ``event`` fields can be safely rendered.

    Unlike ``data`` and ``comment``, these two fields are rendered as-is,
    so a line break or a null byte in them would corrupt the whole stream.

    Works for :class:`~dmr.streaming.sse.metadata.SSEvent`
    and for any custom event type.
    """
    # We use `getattr` here, because the event model can be `Any`,
    # in this case anything at all can reach this point.
    # Missing fields are reported by the renderer, not by us.
    check_event_field(getattr(event, 'id', None), field_name='id')
    check_event_field(getattr(event, 'event', None), field_name='event')
    return event


SSEPipeline: TypeAlias = Callable[
    ['SSE', Any, type['BaseSerializer']],
    'SSE',
]


class SSEStreamingValidator(StreamingValidator):
    """Injects itself into the stream of SSE to validate the events."""

    __slots__ = ()

    @override
    def validation_pipeline(self) -> Iterable[SSEPipeline]:
        """Validate the event type, the event payload, and the event fields."""
        return (
            # Order is important:
            validate_event_type,
            validate_event_data,
            validate_event_fields,
        )
