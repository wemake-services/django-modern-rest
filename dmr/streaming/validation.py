import abc
from collections.abc import Callable, Iterable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Self, TypeVar

from dmr.exceptions import EndpointMetadataError, ValidationError
from dmr.metadata import EndpointMetadata

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.controller import StreamingController


def validate_event_type(
    event: Any,
    model: Any,
    serializer: type['BaseSerializer'],
) -> Any:
    """Validate that the event type matches the model."""
    try:
        serializer.from_python(
            event,
            model=model,
            strict=True,
        )
    except serializer.validation_error as exc:
        raise ValidationError(
            serializer.serialize_validation_error(exc),
        ) from None
    return event


_EventT = TypeVar('_EventT')

_ValidationPipeline = Callable[
    [_EventT, Any, type['BaseSerializer']],
    _EventT,
]


class StreamingValidator:
    """
    Injects itself into the stream of SSE to validate the events.

    This is very different from the the any other validator. Why?

    1. Because we send just one response. No events can be produced
       at all for a long period of time. Some events can be correct,
       while other can be wrong
    2. We can't close the connection when finding wrong events,
       it will be a big problem for our users and it would be hard to debug
    3. But, we can modify events to be ``error`` events instead!
    4. When validation is active and the event
       is either not the model we expect
       or has the wrong payload type - we send the error event

    """

    __slots__ = ('_event_model', '_serializer', '_validate_events')

    def __init__(
        self,
        event_model: Any,
        serializer: type['BaseSerializer'],
        *,
        validate_events: bool,
    ) -> None:
        """Initialize the validator."""
        self._event_model = event_model
        self._serializer = serializer
        self._validate_events = validate_events

    def apply_event_pipeline(self, event: Any) -> Any:
        """Runs the pipeline."""
        if not self._validate_events:
            return event

        for func in self.validation_pipeline():
            event = func(
                event,
                self._event_model,
                self._serializer,
            )
        return event

    @abc.abstractmethod
    def validation_pipeline(self) -> Iterable[_ValidationPipeline[Any]]:
        """Abstract method to define the event validation pipeline."""
        raise NotImplementedError

    @classmethod
    def from_controller(
        cls,
        controller: 'StreamingController[BaseSerializer]',
        status_code: HTTPStatus,
    ) -> Self:
        """
        Construct validator from a controller instance.

        Inferences event type model from the endpoint metadata.
        Also knows whether or not the events validation is turned on or not.
        """
        method = controller.request.method
        # for mypy: it can't be `None` at this point
        assert method is not None  # noqa: S101
        metadata = controller.api_endpoints[method].metadata

        return cls(
            event_model=_resolve_event_model(metadata, status_code),
            serializer=controller.serializer,
            validate_events=metadata.validate_events,
        )


def _resolve_event_model(
    metadata: EndpointMetadata,
    status_code: HTTPStatus,
) -> Any:
    try:
        return metadata.responses[status_code].return_type
    except (KeyError, ValueError):
        if metadata.validate_events:
            raise EndpointMetadataError(
                'Cannot resolve event model for endpoint '
                f'{metadata.endpoint_name!r} and {status_code=}',
            ) from None
        return Any
