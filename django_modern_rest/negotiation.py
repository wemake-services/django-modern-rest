from collections.abc import Sequence
from typing import final

from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from django_modern_rest.exceptions import (
    RequestSerializationError,
    ResponseSerializationError,
)
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.parsers import Parser
from django_modern_rest.renderers import Renderer
from django_modern_rest.serialization import BaseSerializer


class RequestNegotiator:
    """Selects a correct parser type for a request."""

    __slots__ = ('_default', '_parser_types', '_serializer')

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        self._parser_types = metadata.parser_types
        # The first parser is the default one:
        self._default = next(iter(self._parser_types.values()))

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
        if request.content_type is None:
            return self._default
        parser_type = self._parser_types.get(request.content_type)
        if parser_type is None:
            expected = list(self._parser_types.keys())
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

    __slots__ = ('_default', '_renderer_keys', '_renderer_types', '_serializer')

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> None:
        """Initialization happens during an endpoint creation in import time."""
        self._serializer = serializer
        self._renderer_types = metadata.renderer_types
        self._renderer_keys = list(self._renderer_types.keys())
        # The first renderer is the default one:
        self._default = next(iter(self._renderer_types.values()))

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
        if request.headers.get('Accept') is None:
            return self._default
        try:
            renderer_type = request.get_preferred_type(self._renderer_keys)
        except AttributeError:  # pragma: no cover
            # This is a backport of django's 5.2 feature to older djangos.
            renderer_type = _get_preferred_type(request, self._renderer_keys)
        if renderer_type is None:
            expected = self._renderer_keys
            raise ResponseSerializationError(
                self._serializer.error_serialize(
                    'Cannot serialize response body '
                    f'with accepted types {request.accepted_types!r}, '
                    f'{expected=!r}',
                ),
            )
        return self._renderer_types[renderer_type]


@final
class ResponseValidationNegotiator:
    """
    Special type that we use to re-parse our own response body.

    We do this only when response validation is active.
    It should not be used in production directly.
    Think of it as an internal validation helper.
    """

    __slots__ = ('_default', '_parser_types', '_serializer')

    def __init__(
        self,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> None:
        """Called when this object is needed."""
        self._serializer = serializer
        self._parser_types = metadata.parser_types
        # The first parser is the default one:
        self._default = next(iter(self._parser_types.values()))

    def __call__(self, response: HttpResponseBase) -> type[Parser]:
        """Find a correct parser to load response body."""
        # It might be an incorrect response object with incorrect `Content-Type`
        # header or something.
        return self._parser_types.get(
            response.headers['Content-Type'],
            self._default,
        )


def _get_preferred_type(  # pragma: no cover
    request: HttpRequest,
    media_types: Sequence[str],
) -> str | None:
    """
    This is a backport of django's feature from 5.2 to older djangos.

    All credits go to the original django's authors.
    """
    if not media_types or not request.accepted_types:
        return None

    desired_types = [
        (accepted_type, media_type)
        for media_type in media_types
        if (accepted_type := request.accepted_type(media_type)) is not None
    ]

    if not desired_types:
        return None

    # Of the desired media types, select the one which is preferred.
    return min(
        desired_types,
        key=lambda typ: request.accepted_types.index(typ[0]),
    )[1]
