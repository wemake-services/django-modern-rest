import dataclasses
import re
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Mapping,
    Sequence,
)
from http import HTTPStatus
from io import BytesIO
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    NamedTuple,
    TypeAlias,
    final,
)

from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from typing_extensions import TypeVar, override

from dmr.components import Cookies, Headers, Path, Query
from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.endpoint import validate
from dmr.exceptions import ValidationError
from dmr.headers import HeaderSpec
from dmr.internal.negotiation import force_request_renderer
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.parsers import (
    _NoOpParser,  # pyright: ignore[reportPrivateUsage]
)
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer, DeserializableResponse
from dmr.settings import default_renderer
from dmr.sse.validation import validate_event_type

_EventPipeline: TypeAlias = Callable[
    ['SSEData', Any, type[BaseSerializer]],
    'SSEData',
]


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEvent:
    """
    Server sent event.

    Attributes:
        data: Event payload.
        event: Event type.
        id: Unique event's identification.
        retry: The reconnection time.
        comment: Comment about the event.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#fields

    """

    # NOTE: `str | bytes` is not supported by `msgspec`,
    # but, since it is very common to return json
    # which has `bytes` by default in our serializers - we use `bytes`.
    data: bytes | int  # noqa: WPS110
    event: str | None = dataclasses.field(default=None, kw_only=True)
    id: int | str | None = dataclasses.field(default=None, kw_only=True)
    retry: int | None = dataclasses.field(default=None, kw_only=True)
    comment: str | None = dataclasses.field(default=None, kw_only=True)


SSEData: TypeAlias = int | bytes | SSEvent


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEResponse:
    streaming_content: AsyncIterator[SSEData]
    cookies: Mapping[str, NewCookie] | None = None
    headers: Mapping[str, str] | None = None


class SSEStreamingResponse(DeserializableResponse, HttpResponseBase):
    """
    Our own response subclass to mark that we explicitly return SSE.

    Converts events to ``bytes`` with the help of a passed serializer
    and renderer types.
    """

    #: Part of the the ASGI handler protocol. Will trigger `__aiter__`
    streaming: Final = True  # type: ignore[misc]

    validation_pipeline: ClassVar[Sequence[_EventPipeline]] = (
        # Order is important:
        validate_event_type,
    )

    def __init__(
        self,
        streaming_content: AsyncIterator[SSEData],
        serializer: type['BaseSerializer'],
        regular_renderer: Renderer,
        sse_renderer: Renderer,
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

        super().__init__(headers=headers, status=200)
        self._streaming_content = streaming_content
        self.serializer = serializer
        self.regular_renderer = regular_renderer
        self.sse_renderer = sse_renderer
        self.event_schema = event_schema
        if validate_events:
            self._event_pipeline = self.validation_pipeline
        else:
            self._event_pipeline = ()

    @override
    def deserializable_model(self) -> Any:
        return b''

    @override
    def __iter__(self) -> Iterator[bytes]:
        """
        In development it is useful to have sync interface for SSE.

        This is a part of the WSGI handler protocol.

        .. danger::

            Do not use this in production!
            We even added a special error to cache this.
            In production you must use ASGI servers like ``uvicorn`` with SSE.

        """
        # NOTE: DO NOT USE IN PRODUCTION
        if not settings.DEBUG:
            raise RuntimeError('Do not use wsgi with SSE in production')

        async def factory() -> list[bytes]:
            return [chunk async for chunk in self._events_pipeline()]

        return iter(async_to_sync(factory)())

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
        async for event in self._streaming_content:
            try:
                event = self._apply_pipeline(event)
            except Exception as exc:
                event = self.handle_event_error(event, exc)
            yield self._render_event(event)

    def _apply_pipeline(self, event: SSEData) -> SSEData:
        for func in self._event_pipeline:
            event = func(
                event,
                self.event_schema,
                self.serializer,
            )
        return event

    def _render_event(self, event: SSEData) -> bytes:
        return self.serializer.serialize(
            event,
            renderer=self.sse_renderer,
        )


_DEFAULT_SEPARATOR: Final = b'\r\n'
_LINE_BREAK_RE: Final = re.compile(rb'\r\n|\r|\n')


class SSERenderer(Renderer):
    """
    Renders response as a stream of SSE.

    Uses sub-renderer to render events' data into the correct format.
    """

    __slots__ = ('_encoding', '_linebreak', '_sep')

    content_type = 'text/event-stream'

    def __init__(
        self,
        *,
        sep: bytes = _DEFAULT_SEPARATOR,
        encoding: str = 'utf-8',
        linebreak: re.Pattern[bytes] = _LINE_BREAK_RE,
    ) -> None:
        """
        Initialize the renderer.

        Arguments:
            sep: Line and events separator.
            encoding: Encoding to convert string data into bytes.
            linebreak: How to process new lines in event's data.

        """
        self._sep = sep
        self._encoding = encoding
        self._linebreak = linebreak

    @override
    def render(  # noqa: C901, WPS213
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """Render a single event in the SSE chain of events."""
        if not isinstance(to_serialize, SSEvent):
            to_serialize = SSEvent(to_serialize)

        # We use BytesIO, because our json renderer returns `bytes`.
        # We don't want to convert it to string to convert it to bytes again.
        # Payload will always be preset,
        # while other metadata will frequently be missing.
        buffer = BytesIO()

        if to_serialize.comment is not None:
            for chunk in self._linebreak.split(
                to_serialize.comment.encode(self._encoding),
            ):
                buffer.write(b': ')
                buffer.write(chunk)
                buffer.write(self._sep)  # noqa: WPS204

        if to_serialize.id is not None:
            buffer.write(b'id: ')
            buffer.write(
                self._linebreak.sub(
                    b'',
                    str(to_serialize.id).encode(self._encoding),
                ),
            )
            buffer.write(self._sep)

        if to_serialize.event is not None:
            buffer.write(b'event: ')
            buffer.write(
                self._linebreak.sub(
                    b'',
                    to_serialize.event.encode(self._encoding),
                ),
            )
            buffer.write(self._sep)

        if to_serialize.data is not None:
            payload = (
                to_serialize.data
                if isinstance(to_serialize.data, bytes)
                else str(to_serialize.data).encode(self._encoding)
            )
            for chunk in self._linebreak.split(payload):
                buffer.write(b'data: ')
                buffer.write(chunk)
                buffer.write(self._sep)

        if to_serialize.retry is not None:
            buffer.write(b'retry: ')
            buffer.write(str(to_serialize.retry).encode(self._encoding))
            buffer.write(self._sep)

        buffer.write(self._sep)

        return buffer.getvalue()

    @property
    @override
    def validation_parser(self) -> _NoOpParser:
        return _NoOpParser(self.content_type)


class _SSEMetadata(EndpointMetadata):
    default_renderer: ClassVar[Renderer]

    @override
    def collect_response_specs(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: dict[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
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
_InputT = TypeVar('_InputT')
_PathT = TypeVar('_PathT', default=None)
_QueryT = TypeVar('_QueryT', default=None)
_HeadersT = TypeVar('_HeadersT', default=None)
_CookiesT = TypeVar('_CookiesT', default=None)


class SSEContext(NamedTuple, Generic[_PathT, _QueryT, _HeadersT, _CookiesT]):
    parsed_path: _PathT
    parsed_query: _QueryT
    parsed_headers: _HeadersT
    parsed_cookies: _CookiesT


def sse(
    serializer: type[_SerializerT],
    *,
    path: type[Path[_PathT]] | None = None,
    query: type[Query[_QueryT]] | None = None,
    headers: type[Headers[_HeadersT]] | None = None,
    cookies: type[Cookies[_CookiesT]] | None = None,
    response_spec: ResponseSpec | None = None,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool = True,
    validate_events: bool | None = None,
    regular_renderer: Renderer | None = None,
    sse_renderer: SSERenderer | None = None,
    sse_streaming_response_cls: type[
        SSEStreamingResponse
    ] = SSEStreamingResponse,
    metadata_cls: type[EndpointMetadata] = _SSEMetadata,
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
    # All these new variables are needed, because `mypy` can't properly
    # resolved narrower types for them:
    if validate_events is None:
        resolved_validate_events = validate_responses
    else:
        resolved_validate_events = validate_events

    resolved_renderer = regular_renderer or default_renderer
    resolved_sse_renderer = sse_renderer or SSERenderer()

    if response_spec is None:
        resolved_response_spec = ResponseSpec(
            SSEData,
            status_code=HTTPStatus.OK,
            headers={
                'Cache-Control': HeaderSpec(),
                'Connection': HeaderSpec(required=not settings.DEBUG),
                'X-Accel-Buffering': HeaderSpec(),
            },
            limit_to_content_types={resolved_sse_renderer.content_type},
        )
    else:
        resolved_response_spec = response_spec

    modified_metadata_cls = type(
        '_LimitedSSEMetadata',
        (metadata_cls,),
        {'default_renderer': resolved_renderer},
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

        class SSEController(
            Controller[serializer],  # type: ignore[valid-type]
            *filter(None, [path, query, headers, cookies]),  # type: ignore[misc]
        ):
            @override
            def to_error(
                self,
                *args: Any,
                **kwargs: Any,
            ) -> HttpResponse:
                force_request_renderer(self.request, resolved_renderer)
                return super().to_error(*args, **kwargs)

            @validate(
                resolved_response_spec,
                *extra_responses,
                renderers=[resolved_sse_renderer, resolved_renderer],
                validate_responses=validate_responses,
                metadata_cls=modified_metadata_cls,
            )
            async def get(self) -> SSEStreamingResponse:
                context = SSEContext(
                    self.parsed_path if path else None,
                    self.parsed_query if query else None,
                    self.parsed_headers if headers else None,
                    self.parsed_cookies if cookies else None,
                )

                # Now, everything is ready to send SSE events:
                return self.build_sse_streaming_response(
                    await func(
                        self.request,
                        resolved_renderer,
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
                    regular_renderer=resolved_renderer,
                    sse_renderer=resolved_sse_renderer,
                    event_schema=resolved_response_spec.return_type,
                    headers=response.headers,
                    validate_events=resolved_validate_events,
                )
                if response.cookies:
                    for cookie_key, cookie in response.cookies.items():
                        streaming_response.set_cookie(
                            cookie_key,
                            **cookie.as_dict(),
                        )
                return streaming_response

        return SSEController

    return decorator
