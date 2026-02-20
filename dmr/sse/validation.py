from http import HTTPStatus
from typing import TYPE_CHECKING, Any

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
       or has the wrong payload type - we send ``event: error`` SSE event

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
