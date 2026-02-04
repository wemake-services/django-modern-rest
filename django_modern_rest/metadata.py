import dataclasses
from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    final,
)

if TYPE_CHECKING:
    from django_modern_rest.components import ComponentParser
    from django_modern_rest.controller import Controller
    from django_modern_rest.cookies import CookieSpec, NewCookie
    from django_modern_rest.errors import AsyncErrorHandler, SyncErrorHandler
    from django_modern_rest.headers import HeaderSpec, NewHeader
    from django_modern_rest.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Reference,
        Server,
    )
    from django_modern_rest.parsers import Parser
    from django_modern_rest.renderers import Renderer
    from django_modern_rest.security.base import AsyncAuth, SyncAuth
    from django_modern_rest.serializer import BaseSerializer
    from django_modern_rest.settings import HttpSpec

ComponentParserSpec: TypeAlias = tuple[type['ComponentParser'], tuple[Any, ...]]


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ResponseSpec:
    """
    Represents a single API response specification.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response.
        cookies: Shows *cookies* in the documentation.
            When passed, we validate that all given required cookies are present
            in the final response.
        description: Text comment about what this response represents.

    We use this structure to validate responses and render them in OpenAPI.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus = dataclasses.field(kw_only=True)
    headers: Mapping[str, 'HeaderSpec'] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    cookies: Mapping[str, 'CookieSpec'] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    description: str | None = None

    # TODO: examples and other metadata


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ResponseModification:
    """
    Represents a single API modification.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            Headers passed here will be added to the final response.
        cookies: Shows *cookies* in the documentation.
            Cookies passed here will be added to the final response.

    We use this structure to modify the default response.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus
    headers: Mapping[str, 'NewHeader'] | None
    cookies: Mapping[str, 'NewCookie'] | None

    def to_spec(self) -> ResponseSpec:
        """Convert response modification to response description."""
        return ResponseSpec(
            return_type=self.return_type,
            status_code=self.status_code,
            headers=(
                None
                if self.headers is None
                else {
                    header_name: header.to_spec()
                    for header_name, header in self.headers.items()
                }
            ),
            cookies=(
                None
                if self.cookies is None
                else {
                    cookie_key: cookie.to_spec()
                    for cookie_key, cookie in self.cookies.items()
                }
            ),
        )


class ResponseSpecProvider:
    """Base abstract class to provide extra response schemas."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def provide_response_specs(
        cls,
        # Response spec can't be different inside different blueprints.
        # It would be a nightmare to manage.
        # So, controller is the unit of change.
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """
        Provide custom response specs.

        Will be called to inject response specs from different components
        into the resulting endpoint metadata.
        """
        raise NotImplementedError

    @classmethod
    def _add_new_response(
        cls,
        response: ResponseSpec,
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        if response.status_code in existing_responses:
            return []
        return [response]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata:
    """
    Base class for common endpoint metadata.

    Attributes:
        responses: Mapping of HTTP method to response description.
            All possible responses that this API can return.
            Used for OpenAPI spec generation and for response validation.
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
        parsers: List of types to be used for this endpoint
            to parse incoming request's body. All types must be subtypes
            of :class:`~django_modern_rest.parsers.Parser`.
        renderers: List of types to be used for this endpoint
            to render response's body. All types must be subtypes
            of :class:`~django_modern_rest.renderers.Renderer`.
        auth: list of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`django_modern_rest.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`django_modern_rest.security.AsyncAuth`.
            When set it to ``None`` it means that auth
            is disabled for this endpoint.
        no_validate_http_spec: Set of checks that user wants
            to disable for validation in this endpoint.
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
    error_handler: 'SyncErrorHandler | AsyncErrorHandler | None'
    component_parsers: list[ComponentParserSpec]
    parsers: dict[str, type['Parser']]
    renderers: dict[str, type['Renderer']]
    auth: list['SyncAuth | AsyncAuth'] | None
    no_validate_http_spec: frozenset['HttpSpec']

    # OpenAPI documentation fields:
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    deprecated: bool = False
    external_docs: 'ExternalDocumentation | None' = None
    callbacks: dict[str, 'Callback | Reference'] | None = None
    servers: list['Server'] | None = None

    def response_spec_providers(self) -> list[type[ResponseSpecProvider]]:
        """
        Determine: from where we should collect response schemas.

        Override this method in your own metadata classes
        if you want more or less response spec providers.

        For example: you can add some custom field to
        :class:`~django_modern_rest.controller.Controller` like ``checks=``.
        And you can subclass ``EndpointMetadata``
        to also contain ``checks`` field and override this method
        to also include response specs from this field.
        """
        return [
            *[spec[0] for spec in self.component_parsers],
            *self.parsers.values(),
            *self.renderers.values(),
            *[type(auth) for auth in (self.auth or [])],
        ]
