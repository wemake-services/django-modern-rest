from collections.abc import (
    AsyncIterator,
    Callable,
    Iterator,
    Mapping,
    Sequence,
)
from http import HTTPStatus
from typing import Any, ClassVar, Final, TypeAlias

from django.conf import settings
from django.http import HttpResponseBase
from typing_extensions import override

from dmr.exceptions import ValidationError
from dmr.internal.io import aiter_to_iter
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer, DeserializableResponse
from dmr.sse.exceptions import SSECloseConnectionError
from dmr.sse.metadata import SSEData, SSEvent
from dmr.sse.renderer import SSERenderer
from dmr.sse.validation import validate_event_type

_EventPipeline: TypeAlias = Callable[
    ['SSEData', Any, type[BaseSerializer]],
    'SSEData',
]


class SSEStreamingResponse(DeserializableResponse, HttpResponseBase):
    """
    Our own response subclass to mark that we explicitly return SSE.

    Converts events to ``bytes`` with the help of a passed serializer
    and renderer types.
    """

    #: Part of the the ASGI handler protocol. Will trigger `__aiter__`
    streaming: Final = True  # type: ignore[misc]
    is_async: Final = True

    validation_pipeline: ClassVar[Sequence[_EventPipeline]] = (
        # Order is important:
        validate_event_type,
    )

    def __init__(  # noqa: WPS211
        self,
        streaming_content: AsyncIterator[SSEData],
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        sse_renderer: SSERenderer,
        event_schema: Any,
        *,
        headers: Mapping[str, str] | None = None,
        validate_events: bool = True,
    ) -> None:
        """
        Create the SSE streaming response.

        Arguments:
            streaming_content: Events producing async iterator.
            serializer: Serializer type to handle event's data.
            regular_renderer: Render python objects to text format.
            sse_renderer: Render events to bytes according to the SSE protocol.
            event_schema: Schema for all possible produced events.
            headers: Headers to be set on the response.
            validate_events: Should all produced events be validated
                against *event_schema*.

        """
        headers = {} if headers is None else dict(headers)
        headers.update({
            'Cache-Control': 'no-cache',
            'Content-Type': sse_renderer.content_type,
            'X-Accel-Buffering': 'no',
        })
        if not settings.DEBUG:
            # This will not work with the wsgi,
            # which is the default protocol for `runserver`.
            # See `wsgiref` and `is_hop_by_hop` function.
            headers.update({
                'Connection': 'keep-alive',
            })

        super().__init__(headers=headers, status=HTTPStatus.OK)
        self._streaming_content = streaming_content
        self.serializer = serializer
        self.regular_renderer = regular_renderer
        self.sse_renderer = sse_renderer
        self.event_schema = event_schema
        if validate_events:
            self._pipeline = self.validation_pipeline
        else:
            self._pipeline = ()

    @override
    def deserializable_content(self) -> Any:
        """Empty body."""
        return b''

    @override
    def __iter__(self) -> Iterator[bytes]:
        """
        In development it is useful to have sync interface for SSE.

        This is a part of the WSGI handler protocol.

        .. danger::

            Do not use this in production!
            We even added a special error to catch this.
            In production you must use ASGI servers like ``uvicorn`` with SSE.

        This implementation has a lot of limitations.
        Be careful even in development.

        """
        # NOTE: DO NOT USE IN PRODUCTION
        if not settings.DEBUG:
            raise RuntimeError('Do not use WSGI with SSE in production')

        return aiter_to_iter(self._events_pipeline())

    def __aiter__(self) -> AsyncIterator[bytes]:
        """
        ASGI handler protocol for streaming responses.

        When ``streaming`` is ``True``, ASGI handler will async iterate over
        the response object.

        When doing so, we will be inside the ASGI handler already.
        No DMR error handling will work.
        """
        return self._events_pipeline()

    def handle_event_error(
        self,
        event: Any,
        exception: Exception,
    ) -> SSEData:
        """
        Handles errors that can happen while sending events.

        Return alternative event that will indicate what error has happened.
        By default does nothing and just reraises the exception.
        """
        if isinstance(exception, ValidationError):
            return SSEvent(
                self.serializer.serialize(
                    exception.payload,
                    renderer=self.regular_renderer,
                ),
                event='error',
            )
        raise  # noqa: PLE0704

    async def _events_pipeline(self) -> AsyncIterator[bytes]:
        try:
            async for event in self._streaming_content:
                event = self._apply_event_pipeline(event)
                yield self.serializer.serialize(
                    event,
                    renderer=self.sse_renderer,
                )
        except SSECloseConnectionError:
            self.close()

    def _apply_event_pipeline(self, event: SSEData) -> SSEData:
        try:
            for func in self._pipeline:
                event = func(
                    event,
                    self.event_schema,
                    self.serializer,
                )
        except Exception as exc:
            event = self.handle_event_error(event, exc)
        return event
