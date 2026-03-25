from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, get_args

from dmr.exceptions import ValidationError

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


def validate_event_type(
    event: Any,
    model: Any,
    serializer: type['BaseSerializer'],
) -> Any:
    """
    Injects itself into the stream of SSE to validate the events.

    This is very different from the the any other validator. Why?

    1. Because we send just one response. No events can be produced
       at all for a long period of time. Some events can be correct,
       while other can be wrong
    2. We can't close the connection when finding wrong events,
       it will be a big problem for our users and it would be hard to debug
    3. But, we can modify events to be ``error`` events instead!
    4. When validation is active and the event is either not ``SSEvent``
       or has the wrong payload type - we send ``event: error`` event

    """
    try:
        serializer.from_python(
            event,
            model=model,
            strict=True,
        )
    except serializer.validation_error as exc:
        raise ValidationError(
            serializer.serialize_validation_error(exc),
            status_code=HTTPStatus.OK,
        ) from None
    return event


def validate_event_data(
    event: Any,
    model: Any,
    serializer: type['BaseSerializer'],
) -> Any:
    """
    Injects itself into the stream of SSE to validate the events.

    Validates ``SSEvent.data`` to be of the given type arg.
    """
    from dmr.sse.metadata import SSEvent  # noqa: PLC0415

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
            status_code=HTTPStatus.OK,
        ) from None
    return event  # pyright: ignore[reportUnknownVariableType]


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
