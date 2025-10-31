import dataclasses
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    final,
)

from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.response import (
    ResponseModification,
    ResponseSpec,
)

if TYPE_CHECKING:
    from django_modern_rest.components import ComponentParser
    from django_modern_rest.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Reference,
        SecurityRequirement,
        Server,
    )

ComponentParserSpec: TypeAlias = tuple[type['ComponentParser'], tuple[Any, ...]]


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
        component_parsers: List of component parser specifications
            from the controller. Each spec is a tuple
            of (ComponentParser class, type args).
        summary: A short summary of what the operation does.
        description: A verbose explanation of the operation behavior.
        tags: A list of tags for API documentation control.
            Used to group operations in OpenAPI documentation.
        operation_id: Unique string used to identify the operation.
        deprecated: Declares this operation to be deprecated.
        security: A declaration of which security mechanisms can be used
            for this operation. List of security requirement objects.
        external_docs: Additional external documentation for this operation.
        callbacks: A map of possible out-of band callbacks related to the
            parent operation. The key is a unique identifier for the Callback
            Object. Each value in the map is a Callback Object that describes
            a request that may be initiated by the API provider and the
            expected responses.
        servers: An alternative servers array to service this operation.
            If a servers array is specified at the Path Item Object or
            OpenAPI Object level, it will be overridden by this value.

    ``method`` can be a custom name, not specified
    in :class:`http.HTTPMethod` enum, when
    ``allow_custom_http_methods`` is used for endpoint definition.
    This might be useful for cases like when you need
    to define a method like ``query``, which is not yet formally accepted.
    Or provide domain specific HTTP methods.

    .. seealso::

        https://httpwg.org/http-extensions/draft-ietf-httpbis-safe-method-w-body.html

    """

    responses: dict[HTTPStatus, ResponseSpec]
    validate_responses: bool | None
    method: str
    modification: ResponseModification | None
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | None
    component_parsers: list[ComponentParserSpec]

    # OpenAPI documentation fields:
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    deprecated: bool = False
    security: list['SecurityRequirement'] | None = None
    external_docs: 'ExternalDocumentation | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    servers: list['Server'] | None = None
