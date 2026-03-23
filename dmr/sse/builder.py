import dataclasses
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Mapping,
    Sequence,
)
from functools import wraps
from http import HTTPStatus
from typing import Any, ClassVar, get_args

from django.http import HttpRequest, HttpResponse
from typing_extensions import TypeVar, override

from dmr.components import Cookies, Headers, Path, Query
from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.endpoint import Endpoint, validate
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.internal.negotiation import force_request_renderer
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.renderers import Renderer
from dmr.security import AsyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, default_renderer, resolve_setting
from dmr.sse.metadata import SSE, SSEContext, SSEResponse, SSEResponseSpec
from dmr.sse.renderer import SSERenderer
from dmr.sse.stream import SSEStreamingResponse
from dmr.types import parse_return_annotation


class SSEEndpointMetadata(EndpointMetadata):
    """Endpoint metadata for SSE."""

    # Abstract attribute:
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


_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)


class _BaseSSEController(Controller[_SerializerT_co]):
    # Custom attributes for the streaming responses:
    regular_renderer: ClassVar[Renderer] = default_renderer
    sse_streaming_response_cls: ClassVar[type[SSEStreamingResponse]] = (
        SSEStreamingResponse
    )
    metadata_cls: ClassVar[type[SSEEndpointMetadata]] = SSEEndpointMetadata

    # Set in `__init_subclass__`:
    validate_events: ClassVar[bool]
    sse_renderer: ClassVar[SSERenderer]

    # Must be moved elsewhere:
    event_model: ClassVar[Any]

    @override
    def __init_subclass__(cls) -> None:
        metadata_cls = cls.metadata_cls
        metadata_cls = type(
            f'{cls.__qualname__}_{metadata_cls.__qualname__}',
            (metadata_cls,),
            {'default_renderer': cls.regular_renderer},
        )
        cls.endpoint_cls = type(
            f'{cls.__qualname__}_SSEEndpoint',
            (Endpoint,),
            {'metadata_cls': metadata_cls},
        )
        cls.validate_events = getattr(
            cls,
            'validate_events',
            # Defaults to the `validates_responses`:
            bool(cls.validate_responses),
        )

        super().__init_subclass__()

        # TODO: handle abstract controllers:
        cls.sse_renderer = SSERenderer(cls.serializer, cls.regular_renderer)

    @override
    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        force_request_renderer(self.request, self.regular_renderer)
        return super().to_error(
            raw_data,
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            renderer=renderer,
        )

    def to_sse_response(
        self,
        streaming_content: AsyncIterator[SSE],
        *,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
    ) -> SSEStreamingResponse:
        streaming_response = self.sse_streaming_response_cls(
            streaming_content,
            headers=headers,
            event_model=self.event_model,
            serializer=self.serializer,
            regular_renderer=self.regular_renderer,
            sse_renderer=self.sse_renderer,
            validate_events=self.validate_events,
        )
        for cookie_key, cookie in (cookies or {}).items():
            streaming_response.set_cookie(
                cookie_key,
                **cookie.as_dict(),
            )
        return streaming_response


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
    response_spec: SSEResponseSpec | None = None,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool | None = None,
    validate_events: bool | None = None,
    regular_renderer: Renderer | None = None,
    sse_renderer: SSERenderer | None = None,
    sse_streaming_response_cls: type[
        SSEStreamingResponse
    ] = SSEStreamingResponse,
    metadata_cls: type[SSEEndpointMetadata] = SSEEndpointMetadata,
    auth: Sequence[AsyncAuth] | None = (),
) -> Callable[
    [
        Callable[
            [
                HttpRequest,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse[SSE]],
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
        >>> from dmr.sse import SSEContext, SSEResponse, sse, SSEvent

        >>> async def clock_events(
        ...     serializer: type[PydanticSerializer],
        ...     renderer: Renderer,
        ... ) -> AsyncIterator[SSEvent[dt.datetime]]:
        ...     while True:
        ...         yield SSEvent(dt.datetime.now(dt.timezone.utc))
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
        ... ) -> SSEResponse[SSEvent[dt.datetime]]:
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
    sse_renderer = sse_renderer or SSERenderer(serializer, regular_renderer)

    def decorator(  # noqa: WPS234
        func: Callable[
            [
                HttpRequest,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse[SSE]],
        ],
        /,
    ) -> type[Controller[_SerializerT]]:
        nonlocal response_spec  # noqa: WPS420
        event_model = _resolve_event_model(func)
        if response_spec is None:
            response_spec = SSEResponseSpec(event_model)

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
            auth=auth,
            _validate_events=validate_events,
            _regular_renderer=regular_renderer,
            _sse_renderer=sse_renderer,
            _sse_streaming_response_cls=sse_streaming_response_cls,
            _event_model=event_model,
            _metadata_cls=metadata_cls,
        )

    return decorator


def _build_controller(  # noqa: WPS211, WPS234
    serializer: type[_SerializerT],
    func: Callable[
        [
            HttpRequest,
            SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
        ],
        Awaitable[SSEResponse[SSE]],
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
    auth: Sequence[AsyncAuth] | None,
    _validate_events: bool,
    _regular_renderer: Renderer,
    _sse_renderer: SSERenderer,
    _sse_streaming_response_cls: type[SSEStreamingResponse],
    _event_model: Any,
    _metadata_cls: type[SSEEndpointMetadata],
) -> type[Controller[_SerializerT]]:
    # Some parameters names have a `_` prefix, because writing
    # `event_model = `event_model` inside a class is a `NameError`.

    @wraps(func, updated=())
    class SSEController(  # noqa: WPS431
        _BaseSSEController[serializer],  # type: ignore[valid-type]
        *filter(None, [path, query, headers, cookies]),  # type: ignore[misc]  # noqa: WPS606
    ):
        regular_renderer = _regular_renderer
        sse_renderer = _sse_renderer
        validate_events = _validate_events
        event_model = _event_model
        sse_streaming_response_cls = _sse_streaming_response_cls
        metadata_cls = _metadata_cls

        @validate(
            response_spec,
            *extra_responses,
            renderers=[sse_renderer, regular_renderer],
            validate_responses=validate_responses,
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
            response = await func(
                self.request,
                context,  # type: ignore[arg-type]
            )
            return self.to_sse_response(
                response.streaming_content,
                headers=response.headers,
                cookies=response.cookies,
            )

    return SSEController  # pyright: ignore[reportReturnType]


def _resolve_event_model(func: Callable[..., Any]) -> Any:
    return_type = parse_return_annotation(func)
    type_args = get_args(return_type)
    if not type_args:
        raise UnsolvableAnnotationsError(
            'Cannot determine event data model for runtime validation, '
            'did you forget to specify the type arg for SSEResponse?',
        )
    return type_args[0]
