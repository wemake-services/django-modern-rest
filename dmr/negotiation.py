import enum
from collections.abc import Mapping
from functools import lru_cache, partial
from typing import TYPE_CHECKING, Any, Final, Literal, final, overload

from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from dmr.envs import MAX_CACHE_SIZE
from dmr.exceptions import EndpointMetadataError, RequestSerializationError
from dmr.internal.negotiation import ConditionalType as _ConditionalType
from dmr.internal.negotiation import find_parser as _find_parser
from dmr.internal.negotiation import find_renderer as _find_renderer
from dmr.internal.negotiation import (
    get_conditional_types as get_conditional_types,
)
from dmr.internal.negotiation import media_by_precedence, not_acceptable_error
from dmr.metadata import EndpointMetadata
from dmr.parsers import Parser
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from functools import (
        _lru_cache_wrapper,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.serializer import BaseSerializer

_CANNOT_PARSE_MSG: Final = _(
    'Cannot parse request body with'
    ' content type {content_type},'
    ' expected={expected}',
)


class RequestNegotiator:
    """Selects a correct parser type for a request."""

    __slots__ = (
        '_default',
        '_exact_parsers',
        '_media_by_precedence',
        '_negotiate',
        '_parsers',
        '_serializer',
    )

    #: Memoized ``Content-Type`` header value to parser lookup.
    _negotiate: '_lru_cache_wrapper[Parser | None]'

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        self._parsers = metadata.parsers
        self._exact_parsers = {
            content_type: parser
            for content_type, parser in self._parsers.items()
            if '*' not in content_type
        }
        # Compute precedence in advance:
        self._media_by_precedence = media_by_precedence(self._parsers.keys())
        # The last configured parser is the most specific one:
        self._default = next(iter(self._parsers.values()))
        # Almost every client sends the very same `Content-Type` header
        # over and over, so we only decide once per header value.
        # We bind the state, not `self`: caching a bound method would
        # store `self` in the cache that `self` owns, which is a reference
        # cycle. The negotiator would then only ever be freed by the `gc`.
        self._negotiate = lru_cache(maxsize=MAX_CACHE_SIZE)(
            partial(
                _find_parser,
                parsers=self._parsers,
                exact_parsers=self._exact_parsers,
                media_by_precedence=self._media_by_precedence,
                default=self._default,
            ),
        )

    def __call__(self, request: HttpRequest) -> Parser:
        """
        Negotiates which parser to use for parsing this request.

        Based on ``Content-Type`` header.

        Called in runtime.
        Must work for O(1) for the best case scenario because of that.

        Must set ``__dmr_parser__`` request attribute
        if the negotiation is successful.

        Returns:
            Parser class for this request.

        Raises:
            RequestSerializationError: when ``Content-Type`` request
                header is not supported.

        """
        parser = request_parser(request)  # Does it already exist?
        if parser is not None:
            return parser

        # `request.content_type` is already stripped of its params
        # by django, so it makes a good cache key.
        parser = self._negotiate(request.content_type)
        if parser is None:
            # We only memoize the decision, never the error itself,
            # because exceptions keep their tracebacks alive:
            raise RequestSerializationError(
                _CANNOT_PARSE_MSG.format(
                    content_type=repr(request.content_type),
                    expected=repr(list(self._parsers)),
                ),
            )
        request.__dmr_parser__ = parser  # type: ignore[attr-defined]
        return parser

    def clear_cache(self) -> None:
        """
        Drop everything this negotiator has memoized so far.

        Parsers are fixed for an endpoint in import time,
        so this is only needed when they are modified in place:
        in tests or in some very dynamic setups.
        """
        self._negotiate.cache_clear()


class ResponseNegotiator:
    """
    Selects a correct renderer for a response body.

    .. versionchanged:: 0.5.0
        Now it uses a custom algorithm that is x30 times faster
        (when compiled with :ref:`mypyc`) then the original
        :meth:`django.http.HttpRequest.get_preferred_type` way we used before.

    """

    __slots__ = (
        '_default',
        '_negotiate',
        '_negotiate_non_streaming',
        '_non_streaming_default',
        '_non_streaming_renderers',
        '_renderer_keys',
        '_renderers',
        '_serializer',
        '_streaming',
    )

    #: Memoized ``Accept`` header value to renderer lookups.
    _negotiate: '_lru_cache_wrapper[Renderer | None]'
    _negotiate_non_streaming: '_lru_cache_wrapper[Renderer | None]'

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        *,
        streaming: bool,
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        # When `False`, no streaming related negotiation must happen.
        self._streaming = streaming
        self._renderers = metadata.renderers
        self._non_streaming_renderers = {
            renderer_type: renderer
            for renderer_type, renderer in metadata.renderers.items()
            if not renderer.streaming
        }
        self._renderer_keys = list(self._renderers.keys())
        if self._streaming and not self._non_streaming_renderers:
            raise EndpointMetadataError(
                'At least one non-stream renderer is required '
                f'for stream responses, found: {self._renderer_keys!r}',
            )

        # The last configured parser is the most specific one:
        self._default = next(iter(self._renderers.values()))
        # The second one is suitable for errors if it is a stream:
        self._non_streaming_default = next(
            iter(self._non_streaming_renderers.values()),
        )

        # Almost every client sends the very same `Accept` header
        # over and over, so we only negotiate once per header value.
        # We bind the state, not `self`: caching a bound method would
        # store `self` in the cache that `self` owns, which is a reference
        # cycle. The negotiator would then only ever be freed by the `gc`.
        self._negotiate = lru_cache(maxsize=MAX_CACHE_SIZE)(
            partial(
                _find_renderer,
                renderers=self._renderers,
                default=self._default,
            ),
        )
        self._negotiate_non_streaming = lru_cache(maxsize=MAX_CACHE_SIZE)(
            partial(
                _find_renderer,
                renderers=self._non_streaming_renderers,
                default=self._non_streaming_default,
            ),
        )

    def __call__(self, request: HttpRequest) -> Renderer:
        """
        Negotiates which renderer to use for rendering this response.

        Based on ``Accept`` header.

        Called in runtime.
        Must work for O(1) because of that.

        We use :meth:`django.http.HttpRequest.get_preferred_type` inside.
        So, we have exactly the same negotiation rules as django has.

        Must set ``__dmr_renderer__`` request attribute
        if the negotiation is successful.
        Can set ``__dmr_nonstreaming_renderer__`` if working
        with streaming responses.

        Returns:
            Renderer class for this response.

        Raises:
            NotAcceptableError: when ``Accept`` request header is not supported.

        """
        # `META` is the raw environ dict, `request.headers` is a lazily built
        # case-insensitive copy of it, it might still not exist.
        # Let's not trigger it just yet:
        accept = request.META.get('HTTP_ACCEPT')

        renderer = self._negotiate(accept)
        if renderer is None:
            # We only memoize the decision, never the error itself:
            # its message quotes the accepted types of this exact request.
            raise not_acceptable_error(request, self._renderers)
        request.__dmr_renderer__ = renderer  # type: ignore[attr-defined]
        if self._streaming:
            non_streaming = self._negotiate_non_streaming(accept)
            if non_streaming is None:
                # Main (streaming) negotiation already succeeded.
                # A non-streaming renderer is only needed for 4xx/5xx
                # error bodies and response validation — fall back to
                # the configured default so those paths keep working
                # for clients that only accept the streaming media
                # type (e.g. browser ``EventSource``).
                non_streaming = self._non_streaming_default
            request.__dmr_nonstreaming_renderer__ = non_streaming  # type: ignore[attr-defined]
        return renderer

    def clear_cache(self) -> None:
        """
        Drop everything this negotiator has memoized so far.

        Renderers are fixed for an endpoint in import time,
        so this is only needed when they are modified in place:
        in tests or in some very dynamic setups.
        """
        self._negotiate.cache_clear()
        self._negotiate_non_streaming.cache_clear()


@overload
def request_parser(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> Parser: ...


@overload
def request_parser(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> Parser | None: ...


def request_parser(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> Parser | None:
    """
    Get parser used to parse this request.

    When *strict* is passed and *request* has no parser,
    we raise :exc:`AttributeError`.

    .. note::

        Since request parsing is only used when there's
        a :data:`dmr.components.Body` or similar component,
        there might be no parser at all.

    """
    parser = getattr(request, '__dmr_parser__', None)
    if parser is None and strict:
        raise AttributeError('__dmr_parser__')
    return parser


@overload
def request_renderer(
    request: HttpRequest,
    *,
    strict: Literal[True],
    use_nonstreaming_renderer: bool = False,
) -> Renderer: ...


@overload
def request_renderer(
    request: HttpRequest,
    *,
    strict: bool = False,
    use_nonstreaming_renderer: bool = False,
) -> Renderer | None: ...


def request_renderer(
    request: HttpRequest,
    *,
    strict: bool = False,
    use_nonstreaming_renderer: bool = False,
) -> Renderer | None:
    """
    Get pre-negotiated renderer.

    First, tries a special ``__dmr_nonstreaming_renderer__`` case,
    which will be different for ``streaming`` responses.
    For example: for SSE controllers ``__dmr_nonstreaming_renderer__``
    will be just ``json`` or ``xml``.
    It is not used for REST endpoints.

    While ``__dmr_renderer__`` will be whatever ``Accept`` header
    contains as the first value.

    When *strict* is passed and *request* has no renderer,
    we raise :exc:`AttributeError`.

    .. note::

        There might not be a response renderer that fits what client has asked.
        So, it can return ``None``.

    """
    if use_nonstreaming_renderer:
        # There can be a separate non stream response renderer negotiated
        # for streaming response.
        nonstreaming_renderer = getattr(
            request,
            '__dmr_nonstreaming_renderer__',
            None,
        )
        if nonstreaming_renderer is not None:
            return nonstreaming_renderer  # type: ignore[no-any-return]

    # Fallback to the default one:
    renderer = getattr(request, '__dmr_renderer__', None)
    if renderer is None and strict:
        raise AttributeError('__dmr_renderer__')
    return renderer


@final
@enum.unique
class ContentType(enum.StrEnum):
    """
    Enumeration of frequently used content types.

    Attributes:
        json: ``'application/json'`` format.
        xml: ``'application/xml'`` format.
        x_www_form_urlencoded: ``'application/x-www-form-urlencoded'`` format.
        multipart_form_data: ``'multipart/form-data'`` format.
        msgpack: ``'application/msgpack'`` format.
        event_stream: ``'text/event-stream'`` format for SSE streaming.
        jsonl: ``'application/jsonl'`` format for JSON Lines streaming.
        json_problem_details: ``'application/problem+json'`` format
            for RFC 9457.

    """

    json = 'application/json'
    xml = 'application/xml'
    x_www_form_urlencoded = 'application/x-www-form-urlencoded'
    multipart_form_data = 'multipart/form-data'
    msgpack = 'application/msgpack'
    event_stream = 'text/event-stream'
    jsonl = 'application/jsonl'
    json_problem_details = 'application/problem+json'


def conditional_type(
    mapping: Mapping[str | ContentType, Any],
) -> _ConditionalType:
    """
    Create conditional validation for different content types.

    It is rather usual to see a requirement like:
    - If this method returns ``json`` then we should follow schema1
    - If this methods returns ``xml`` then we should follow schema2

    """
    if len(mapping) <= 1:
        raise EndpointMetadataError(
            'conditional_type must be called with a mapping of length >= 2, '
            f'got {mapping}',
        )
    return _ConditionalType(mapping)


def accepts(request: HttpRequest, content_type: str) -> bool:
    """Determine whether this *request* accepts a given *content_type*."""
    renderer = request_renderer(request)
    return renderer is not None and renderer.content_type == content_type
