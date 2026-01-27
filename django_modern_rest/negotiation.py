import enum
from collections.abc import Mapping
from typing import Any, final

from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from django_modern_rest.exceptions import (
    EndpointMetadataError,
    RequestSerializationError,
    ResponseSerializationError,
)
from django_modern_rest.internal.negotiation import (
    ConditionalType as _ConditionalType,
)
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.parsers import Parser
from django_modern_rest.renderers import Renderer
from django_modern_rest.serialization import BaseSerializer


class RequestNegotiator:
    """Selects a correct parser type for a request."""

    __slots__ = ('_default', '_parsers', '_serializer')

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        self._parsers = metadata.parsers
        # The last configured parser is the most specific one:
        self._default = next(reversed(self._parsers.values()))

    def __call__(self, request: HttpRequest) -> type[Parser]:
        """
        Negotiates which parser to use for parsing this request.

        Based on ``Content-Type`` header.

        Called in runtime.
        Must work for O(1) because of that.

        Raises:
            RequestSerializationError: when ``Content-Type`` request
                header is not supported.

        Returns:
            Parser class for this request.

        """
        parser_cls = self._decide(request)
        request._dmr_parser_cls = parser_cls  # type: ignore[attr-defined]  # noqa: SLF001
        return parser_cls

    def _decide(self, request: HttpRequest) -> type[Parser]:
        if request.content_type is None:
            return self._default
        parser_type = self._parsers.get(request.content_type)
        if parser_type is None:
            expected = list(self._parsers.keys())
            raise RequestSerializationError(
                self._serializer.error_serialize(
                    'Cannot parse request body '
                    f'with content type {request.content_type!r}, '
                    f'{expected=!r}',
                ),
            )
        return parser_type


class ResponseNegotiator:
    """Selects a correct renderer for a response body."""

    __slots__ = ('_default', '_renderer_keys', '_renderers', '_serializer')

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        self._renderers = metadata.renderers
        self._renderer_keys = list(self._renderers.keys())
        # The last configured parser is the most specific one:
        self._default = next(reversed(self._renderers.values()))

    def __call__(self, request: HttpRequest) -> type[Renderer]:
        """
        Negotiates which parser to use for parsing this request.

        Based on ``Content-Type`` header.

        Called in runtime.
        Must work for O(1) because of that.

        We use :meth:`django.http.HttpRequest.get_preferred_type` inside.
        So, we have exactly the same negotiation rules as django has.

        Raises:
            ResponseSerializationError: when ``Accept`` request
                header is not supported.

        Returns:
            Renderer class for this response.

        """
        renderer_cls = self._decide(request)
        request._dmr_renderer_cls = renderer_cls  # type: ignore[attr-defined]  # noqa: SLF001
        return renderer_cls

    def _decide(self, request: HttpRequest) -> type[Renderer]:
        if request.headers.get('Accept') is None:
            return self._default
        renderer_type = request.get_preferred_type(self._renderer_keys)
        if renderer_type is None:
            expected = self._renderer_keys
            raise ResponseSerializationError(
                self._serializer.error_serialize(
                    'Cannot serialize response body '
                    f'with accepted types {request.accepted_types!r}, '
                    f'{expected=!r}',
                ),
            )
        return self._renderers[renderer_type]


def request_parser(request: HttpRequest) -> type[Parser] | None:
    """
    Get parser_cls used to parse this request.

    .. note::

        Since request parsing is only used when there's
        a :class:`django_modern_rest.components.Body` component,
        there might be no parser.

    """
    return getattr(request, '_dmr_parser_cls', None)


def request_renderer(request: HttpRequest) -> type[Renderer] | None:
    """
    Get parser_cls used to parse this request.

    .. note::

        Since request rendering is only used when using raw endpoints,
        there might be no request renderer. Also, renderer is chosen late
        in the life-cycle of the request handling, so there might not be
        a request renderer *yet*.

    """
    return getattr(request, '_dmr_renderer_cls', None)


def response_validation_negotiator(
    request: HttpRequest,
    response: HttpResponseBase,
    metadata: EndpointMetadata,
) -> type[Parser]:
    """
    Special type that we use to re-parse our own response body.

    We do this only when response validation is active.
    It should not be used in production directly.
    Think of it as an internal validation helper.
    """
    parser_types = metadata.parsers
    renderer_type = request_renderer(request)
    if renderer_type is None:
        content_type = response.headers['Content-Type']
    else:
        content_type = renderer_type.content_type

    return parser_types.get(
        content_type,
        next(reversed(parser_types.values())),
    )


@final
@enum.unique
class ContentType(enum.StrEnum):
    """
    Enumeration of frequently used content types.

    Attributes:
        json: ``'application/json'`` format.
        xml: ``'application/xml'`` format.
        x_www_form_urlencoded: ``'application/x-www-form-urlencoded'`` format.
        form_data: ``'multipart/form-data'`` format.

    """

    json = 'application/json'
    xml = 'application/xml'
    x_www_form_urlencoded = 'application/x-www-form-urlencoded'
    form_data = 'multipart/form-data'


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
