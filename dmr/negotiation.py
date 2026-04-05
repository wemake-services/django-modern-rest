import enum
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final, final

from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from dmr.exceptions import EndpointMetadataError, RequestSerializationError
from dmr.internal.negotiation import ConditionalType as _ConditionalType
from dmr.internal.negotiation import media_by_precedence
from dmr.internal.negotiation import negotiate_renderer as _negotiate_renderer
from dmr.metadata import EndpointMetadata, get_annotated_metadata
from dmr.parsers import Parser
from dmr.renderers import Renderer

if TYPE_CHECKING:
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
        '_parsers',
        '_serializer',
    )

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

        parser = self._decide(request)
        request.__dmr_parser__ = parser  # type: ignore[attr-defined]
        return parser

    def _decide(self, request: HttpRequest) -> Parser:
        if request.content_type is None:
            return self._default
        # Try the exact match first, since it is faster, O(1):
        parser_type = self._exact_parsers.get(request.content_type)
        if parser_type is not None:
            # Do not allow invalid content types to be matched exactly.
            return parser_type

        # Now, try to find parser types based on `*/*` patterns, O(n):
        for media in self._media_by_precedence:
            if media.match(request.content_type):
                return self._parsers[str(media)]

        # No parsers found, raise an error:
        expected = list(self._parsers.keys())
        raise RequestSerializationError(
            _CANNOT_PARSE_MSG.format(
                content_type=repr(request.content_type),
                expected=repr(expected),
            ),
        )


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
        '_non_streaming_default',
        '_non_streaming_renderers',
        '_renderer_keys',
        '_renderers',
        '_serializer',
        '_streaming',
    )

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
        renderer = _negotiate_renderer(
            request,
            self._renderers,
            default=self._default,
        )
        request.__dmr_renderer__ = renderer  # type: ignore[attr-defined]
        if self._streaming:
            request.__dmr_nonstreaming_renderer__ = _negotiate_renderer(  # type: ignore[attr-defined]
                request,
                self._non_streaming_renderers,
                default=self._non_streaming_default,
            )
        return renderer


def request_parser(request: HttpRequest) -> Parser | None:
    """
    Get parser used to parse this request.

    .. note::

        Since request parsing is only used when there's
        a :data:`dmr.components.Body` or similar component,
        there might be no parser at all.

    """
    return getattr(request, '__dmr_parser__', None)


def request_renderer(
    request: HttpRequest,
    *,
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
    return getattr(request, '__dmr_renderer__', None)


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

    """

    json = 'application/json'
    xml = 'application/xml'
    x_www_form_urlencoded = 'application/x-www-form-urlencoded'
    multipart_form_data = 'multipart/form-data'
    msgpack = 'application/msgpack'
    event_stream = 'text/event-stream'
    jsonl = 'application/jsonl'


def conditional_type(
    mapping: Mapping[ContentType, Any],
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
    return _ConditionalType(tuple(mapping.items()))


def get_conditional_types(
    model: Any,
    model_meta: tuple[Any, ...],
) -> Mapping[str, Any] | None:
    """
    Returns possible conditional types.

    Conditional types are defined with :data:`typing.Annotated`
    and :func:`dmr.negotiation.conditional_type` helper.
    """
    metadata = get_annotated_metadata(model, model_meta, _ConditionalType)
    if metadata:
        return metadata.computed
    return None
