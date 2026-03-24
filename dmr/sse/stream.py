from collections.abc import (
    AsyncIterator,
    Iterator,
    Mapping,
)
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from django.conf import settings
from django.http import HttpResponseBase
from typing_extensions import override

from dmr.errors import ErrorModel
from dmr.exceptions import ValidationError
from dmr.internal.io import aiter_to_iter, maybe_aclosing
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse.exceptions import SSECloseConnectionError
from dmr.sse.metadata import SSE, SSEvent
from dmr.sse.renderer import SSERenderer

if TYPE_CHECKING:
    from dmr.sse.validation import StreamValidator


class SSEStreamingResponse(HttpResponseBase):
    """
    Our own response subclass to mark that we explicitly return SSE.

    Converts events to ``bytes`` with the help of a passed serializer
    and renderer types.

    We don't inherit from the ``StreamingResponse`` here, because
    it has a strict API for streaming that we can't use.
    """

    #: Part of the the ASGI handler protocol. Will trigger `__aiter__`
    streaming: Final = True  # type: ignore[misc]
    is_async: Final = True

    def __init__(  # noqa: WPS211
        self,
        streaming_content: AsyncIterator[SSE],
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        sse_renderer: SSERenderer,
        *,
        validate_events: bool | None,
        headers: Mapping[str, str] | None = None,
        status_code: HTTPStatus = HTTPStatus.OK,
        stream_validator: 'StreamValidator | None' = None,
    ) -> None:
        """
        Create the SSE streaming response.

        Arguments:
            streaming_content: Events producing async iterator.
            serializer: Serializer type to handle event's data.
            regular_renderer: Render python objects to text format.
            sse_renderer: Render events to bytes according to the SSE protocol.
            validate_events: Should all produced events be validated
                against *event_model*.
            headers: Headers to be set on the response.
            status_code: Status code for the response.
            stream_validator: Stream validator for events.

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

        super().__init__(headers=headers, status=status_code)
        self._streaming_content = streaming_content
        self.serializer = serializer
        self.regular_renderer = regular_renderer
        self.sse_renderer = sse_renderer
        self.validate_events = validate_events
        self.stream_validator = stream_validator

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

        return aiter_to_iter(self._produce_events())

    def __aiter__(self) -> AsyncIterator[bytes]:
        """
        ASGI handler protocol for streaming responses.

        When ``streaming`` is ``True``, ASGI handler will async iterate over
        the response object.

        When doing so, we will be inside the ASGI handler already.
        No DMR error handling will work.
        """
        return self._produce_events()

    def handle_event_error(
        self,
        event: Any,
        exception: Exception,
    ) -> SSE:
        """
        Handles errors that can happen while sending events.

        Return alternative event that will indicate what error has happened.
        By default does nothing and just reraises the exception.
        """
        if isinstance(exception, ValidationError):
            return SSEvent(
                # TODO: change to accept `controller.format_error`,
                # so it can be changed accordingly
                ErrorModel(detail=exception.payload),
                event='error',
            )
        raise  # noqa: PLE0704

    async def _produce_events(self) -> AsyncIterator[bytes]:
        async with maybe_aclosing(self._streaming_content):
            try:
                async for event in self._streaming_content:
                    yield self.serializer.serialize(
                        self._apply_validator(event),
                        renderer=self.sse_renderer,
                    )
            except SSECloseConnectionError:
                self.close()

    def _apply_validator(self, event: SSE) -> SSE:
        if self.stream_validator is None:
            return event
        try:
            return self.stream_validator.apply_event_pipeline(event)
        except Exception as exc:
            return self.handle_event_error(event, exc)
