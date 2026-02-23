import dataclasses
from collections.abc import (
    Awaitable,
    Callable,
    Sequence,
)
from http import HTTPStatus
from typing import Any, ClassVar

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from typing_extensions import TypeVar, override

from dmr.components import Cookies, Headers, Path, Query
from dmr.controller import Controller
from dmr.endpoint import validate
from dmr.headers import HeaderSpec
from dmr.internal.negotiation import force_request_renderer
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.renderers import Renderer
from dmr.security import AsyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, default_renderer, resolve_setting
from dmr.sse.metadata import SSEContext, SSEData, SSEResponse
from dmr.sse.renderer import SSERenderer
from dmr.sse.stream import SSEStreamingResponse


class _SSEMetadata(EndpointMetadata):
    default_renderer: ClassVar[Renderer]

    @override
    def collect_response_specs(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: dict[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """
        Overrides how we collect response specs.

        Limits all responses at this point to the default renderer.
        Because SSE can't return any status codes that are not ``200``.
        """
        all_responses = super().collect_response_specs(
            controller_cls,
            existing_responses,
        )
        return [
            dataclasses.replace(
                response,
                limit_to_content_types={self.default_renderer.content_type},
            )
            for response in all_responses
        ]


_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_PathT = TypeVar('_PathT', default=None)
_QueryT = TypeVar('_QueryT', default=None)
_HeadersT = TypeVar('_HeadersT', default=None)
_CookiesT = TypeVar('_CookiesT', default=None)


def sse(  # noqa: WPS211, WPS234
    serializer: type[_SerializerT],
    *,
    path: type[Path[_PathT]] | None = None,
    query: type[Query[_QueryT]] | None = None,
    headers: type[Headers[_HeadersT]] | None = None,
    cookies: type[Cookies[_CookiesT]] | None = None,
    response_spec: ResponseSpec | None = None,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool | None = None,
    validate_events: bool | None = None,
    regular_renderer: Renderer | None = None,
    sse_renderer: SSERenderer | None = None,
    sse_streaming_response_cls: type[
        SSEStreamingResponse
    ] = SSEStreamingResponse,
    metadata_cls: type[EndpointMetadata] = _SSEMetadata,
    auth: Sequence[AsyncAuth] | None = None,
) -> Callable[
    [
        Callable[
            [
                HttpRequest,
                Renderer,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse],
        ],
    ],
    type[Controller[_SerializerT]],
]:
    """
    Create stream of server sent events.

    An example that produces current timestamps every second.
    Aka "the world's slowest clock implementation" :)

    First, you will need to define an async iterator that will produce events:

    .. code:: python

        >>> import asyncio
        >>> import datetime as dt
        >>> from collections.abc import AsyncIterator

        >>> from django.http import HttpRequest

        >>> from dmr.plugins.pydantic import PydanticSerializer
        >>> from dmr.renderers import Renderer
        >>> from dmr.sse import SSEContext, SSEData, SSEResponse, sse

        >>> async def clock_events(
        ...     serializer: type[PydanticSerializer],
        ...     renderer: Renderer,
        ... ) -> AsyncIterator[SSEData]:
        ...     while True:
        ...         yield dt.datetime.now(dt.timezone.utc).timestamp()
        ...         await asyncio.sleep(1)

    .. danger::

        WSGI handers do not support streaming responses, including SSE,
        by default. You would need to use ASGI handler for SSE endpoints.

        We allow running SSE during ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with SSE.

    Now, let's define our callback that will return
    :class:`~dmr.sse.metadata.SSEResponse` instance with the event source:

    .. code:: python

        >>> @sse(PydanticSerializer)
        ... def clock_view(
        ...     request: HttpRequest,
        ...     renderer: Renderer,
        ...     context: SSEContext,
        ... ) -> SSEResponse:
        ...     return SSEResponse(clock_events())

    ``clock_view`` will be a :class:`~dmr.controller.Controller` instance
    with a single ``GET`` endppoint,
    which will return a streaming response
    with the correct default headers and ``200`` status code.

    We don't expose the controller itself, because it is quite complicated.

    Arguments:
        serializer: Required serializer type.
            Will be used to serialize events and other responses.
        path: Optional :class:`~dmr.components.Path` component type
            to parse path parameters. Will be passed as the context.
        query: Optional :class:`~dmr.components.Query` component type
            to parse query parameters. Will be passed as the context.
        headers: Optional :class:`~dmr.components.Headers` component type
            to parse headers. Will be passed as the context.
        cookies: Optional :class:`~dmr.components.Cookies` component type
            to parse cookies. Will be passed as the context.
        response_spec: Optional override for the default response spec.
            Needed if you provided custom headers, cookies, or API errors
        extra_responses: Extra response specs for non-default status codes.
            Needed if you raise custom errors with custom error codees.
        validate_responses: Optional flag to disable strict response validation.
            See :ref:`response_validation` for more info.
        validate_events: Optional flag to disable strict events validation.
            We recommend keeping event and response validation on
            in development and turn it off in production for better performance.
        regular_renderer: Optional instance of :class:`~dmr.renderers.Renderer`
            to render errors, default event bodies, etc.
        sse_renderer: Optional instance of
            :class:`~dmr.sse.renderer.SSERenderer` to render events stream.
        sse_streaming_response_cls: Optional
            :class:`~dmr.sse.stream.SSEStreamingResponse` subtype
            to actually return ASGI compatible streaming response.
        metadata_cls: Optional :class:`~dmr.metadata.EndpointMetadata` subtype
            to be used to populate ``GET`` endpoint metadata.
        auth: Sequence of auth instances to be used for this SSE controller.
            SSE endpoints must use instances
            of :class:`~dmr.security.AsyncAuth`.
            Set it to ``None`` to disable auth for this SSE controller.

    .. important::

        Any errors that will happen inside events' async iterator
        will not be handled by default. It is a user's job to handle them.

    See also:
        https://html.spec.whatwg.org/multipage/server-sent-events.html

    """
    if validate_responses is None:
        validate_responses = resolve_setting(Settings.validate_responses)
        # For mypy:
        assert isinstance(validate_responses, bool)  # noqa: S101
    if validate_events is None:
        validate_events = validate_responses

    regular_renderer = regular_renderer or default_renderer
    sse_renderer = sse_renderer or SSERenderer()

    if response_spec is None:
        response_spec = ResponseSpec(
            SSEData,
            status_code=HTTPStatus.OK,
            headers={
                'Cache-Control': HeaderSpec(),
                'Connection': HeaderSpec(required=not settings.DEBUG),
                'X-Accel-Buffering': HeaderSpec(),
            },
            limit_to_content_types={sse_renderer.content_type},
        )

    def decorator(
        func: Callable[
            [
                HttpRequest,
                Renderer,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse],
        ],
        /,
    ) -> type[Controller[_SerializerT]]:

        return _build_controller(
            serializer,
            func,
            path=path,
            query=query,
            headers=headers,
            cookies=cookies,
            response_spec=response_spec,
            extra_responses=extra_responses,
            validate_responses=validate_responses,
            validate_events=validate_events,
            regular_renderer=regular_renderer,
            sse_renderer=sse_renderer,
            sse_streaming_response_cls=sse_streaming_response_cls,
            auth=auth,
            metadata_cls=type(
                '_LimitedSSEMetadata',
                (metadata_cls,),
                {'default_renderer': regular_renderer},
            ),
        )

    return decorator


def _build_controller(  # noqa: WPS211, WPS234
    serializer: type[_SerializerT],
    func: Callable[
        [
            HttpRequest,
            Renderer,
            SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
        ],
        Awaitable[SSEResponse],
    ],
    /,
    *,
    path: type[Path[_PathT]] | None,
    query: type[Query[_QueryT]] | None,
    headers: type[Headers[_HeadersT]] | None,
    cookies: type[Cookies[_CookiesT]] | None,
    response_spec: ResponseSpec,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool = True,
    validate_events: bool,
    regular_renderer: Renderer,
    sse_renderer: SSERenderer,
    sse_streaming_response_cls: type[SSEStreamingResponse],
    metadata_cls: type[EndpointMetadata],
    auth: Sequence[AsyncAuth] | None = (),
) -> type[Controller[_SerializerT]]:
    class SSEController(  # noqa: WPS431
        Controller[serializer],  # type: ignore[valid-type]
        *filter(None, [path, query, headers, cookies]),  # type: ignore[misc]  # noqa: WPS606
    ):
        @override
        def to_error(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            force_request_renderer(self.request, regular_renderer)
            return super().to_error(*args, **kwargs)

        @validate(
            response_spec,
            *extra_responses,
            renderers=[sse_renderer, regular_renderer],
            validate_responses=validate_responses,
            metadata_cls=metadata_cls,
            auth=auth,
        )
        async def get(self) -> SSEStreamingResponse:
            context = SSEContext(  # pyright: ignore[reportUnknownVariableType]
                self.parsed_path if path else None,  # pyright: ignore[reportUnknownMemberType]
                self.parsed_query if query else None,  # pyright: ignore[reportUnknownMemberType]
                self.parsed_headers if headers else None,  # pyright: ignore[reportUnknownMemberType]
                self.parsed_cookies if cookies else None,  # pyright: ignore[reportUnknownMemberType]
            )

            # Now, everything is ready to send SSE events:
            return self.build_sse_streaming_response(
                await func(
                    self.request,
                    regular_renderer,
                    context,  # type: ignore[arg-type]
                ),
            )

        def build_sse_streaming_response(
            self,
            response: SSEResponse,
        ) -> SSEStreamingResponse:
            streaming_response = sse_streaming_response_cls(
                response.streaming_content,
                serializer=serializer,
                regular_renderer=regular_renderer,
                sse_renderer=sse_renderer,
                event_schema=response_spec.return_type,
                headers=response.headers,
                validate_events=validate_events,
            )
            for cookie_key, cookie in (response.cookies or {}).items():
                streaming_response.set_cookie(
                    cookie_key,
                    **cookie.as_dict(),
                )
            return streaming_response

    return SSEController
