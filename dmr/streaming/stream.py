import asyncio
from collections.abc import AsyncIterator, Iterator, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from django.conf import settings
from django.http import HttpResponseBase
from typing_extensions import override

from dmr.internal.io import aiter_to_iter, maybe_aclosing
from dmr.renderers import Renderer
from dmr.streaming.exceptions import StreamingCloseError

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer
    from dmr.streaming.controller import StreamingController
    from dmr.streaming.renderer import StreamingRenderer
    from dmr.streaming.validation import StreamingValidator


class StreamingResponse(HttpResponseBase):  # noqa: WPS338
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
        streaming_content: AsyncIterator[Any],
        controller: 'StreamingController[BaseSerializer]',
        *,
        regular_renderer: Renderer,
        streaming_renderer: 'StreamingRenderer',
        streaming_validator: 'StreamingValidator',
        headers: Mapping[str, str] | None = None,
        status_code: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        """
        Create the streaming response.

        Arguments:
            streaming_content: Events producing async iterator.
            controller: Controller to handle event's data.
            regular_renderer: Render python objects to text format.
            streaming_renderer: Render events to bytes according
                to streaming protocol rules.
            streaming_validator: Stream validator for events.
            headers: Headers to be set on the response.
            status_code: Status code for the response.

        """
        headers = {} if headers is None else dict(headers)
        # Content-Type must be a str type, as wsgiref checks that
        # to use str type.
        headers.update({
            'Cache-Control': 'no-cache',
            'Content-Type': str(streaming_renderer.content_type),
            'X-Accel-Buffering': 'no',
        })
        if not settings.DEBUG:
            # This will not work with the wsgi,
            # which is the default protocol for `runserver`.
            # See `wsgiref` and `is_hop_by_hop` function.
            headers.update({'Connection': 'keep-alive'})

        super().__init__(headers=headers, status=status_code)
        self._streaming_content = streaming_content
        self._controller = controller
        self.regular_renderer = regular_renderer
        self.streaming_renderer = streaming_renderer
        self.streaming_validator = streaming_validator

    # Why?
    # Because it is only used by ASGI / WSGI handlers which don't care
    # about typing at all. But, it helps to prevent different user errors.
    if not TYPE_CHECKING:  # pragma: no branch  # noqa: WPS604

        @override
        def __iter__(self) -> Iterator[bytes]:
            """
            In development it is useful to have sync interface for streaming.

            This is a part of the WSGI handler protocol.

            .. danger::

                Do not use this in production!
                We even added a special error to catch this.
                In production you must use ASGI servers
                like ``uvicorn`` with streaming.

            This implementation has a lot of limitations.
            Be careful even in development.

            """
            # NOTE: DO NOT USE IN PRODUCTION
            if not settings.DEBUG:
                raise RuntimeError(
                    'Do not use WSGI with event streaming in production',
                )

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

        def close(self) -> None:
            """Closes the response and cleans up all references."""
            super().close()
            # Explicitly break ref cycles:
            self._controller = None
            self.regular_renderer = None
            self.streaming_renderer = None
            self.streaming_validator = None

    async def _produce_events(self) -> AsyncIterator[bytes]:
        async with maybe_aclosing(self._streaming_content):
            while True:
                try:
                    event = self._apply_validator(
                        await anext(self._streaming_content),
                    )
                except (
                    StreamingCloseError,
                    asyncio.CancelledError,
                    StopAsyncIteration,
                ):
                    self.close()
                    break
                except Exception as exc:
                    event = await self._handle_event_error(exc)

                yield self._controller.serializer.serialize(
                    event,
                    renderer=self.streaming_renderer,
                )

    def _apply_validator(self, event: Any) -> Any:
        return self.streaming_validator.apply_event_pipeline(event)

    async def _handle_event_error(
        self,
        exc: Exception,
    ) -> Any:
        """
        Handles errors that can happen while sending events.

        Return alternative event that will indicate what error has happened.
        By default does nothing and just reraises the exception.
        """
        try:
            return await self._controller.handle_event_error(exc)
        except Exception as sub:
            raise sub from exc
