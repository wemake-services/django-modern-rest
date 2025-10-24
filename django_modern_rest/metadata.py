import dataclasses
from http import HTTPStatus
from typing import (
    final,
)

from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.response import (
    ResponseDescription,
    ResponseModification,
)
from django_modern_rest.types import Empty


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata:
    """
    Base class for common endpoint metadata.

    Attributes:
        responses: Mapping of HTTP method to response description.
            All possible responses that this API can return.
        method: String name of an HTTP method for this endpoint.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        modification: Default modifications that are applied
            to the returned data. Can be ``None``, when ``@validate`` is used.
        error_handler: Callback function to be called
            when this endpoint faces an exception.

    ``method`` can be a custom name, not specified
    in :class:`http.HTTPMethod` enum, when
    ``allow_custom_http_methods`` is used for endpoint definition.
    This might be useful for cases like when you need
    to define a method like ``query``, which is not yet formally accepted.
    Or provide domain specific HTTP methods.

    .. seealso::

        https://httpwg.org/http-extensions/draft-ietf-httpbis-safe-method-w-body.html

    """

    responses: dict[HTTPStatus, ResponseDescription]
    validate_responses: bool | Empty
    method: str
    modification: ResponseModification | None
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | Empty
