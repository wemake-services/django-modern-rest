import dataclasses
from abc import abstractmethod
from collections.abc import Mapping, Set
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, final

if TYPE_CHECKING:
    from dmr.components import ComponentParser
    from dmr.controller import Controller
    from dmr.cookies import CookieSpec, NewCookie
    from dmr.errors import AsyncErrorHandler, SyncErrorHandler
    from dmr.headers import HeaderSpec, NewHeader
    from dmr.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Reference,
        Server,
    )
    from dmr.parsers import Parser
    from dmr.renderers import Renderer
    from dmr.security.base import AsyncAuth, SyncAuth
    from dmr.serializer import BaseSerializer
    from dmr.settings import HttpSpec

ComponentParserSpec: TypeAlias = tuple[type['ComponentParser'], tuple[Any, ...]]


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ResponseSpec:
    """
    Represents a single API response specification.

    Attributes:
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
        limit_to_content_types: This response can only happen
            only for given content types. By default, when equals to ``None``,
            all responses can happen for all content types.

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
    description: str | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    limit_to_content_types: Set[str] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )


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
            New cookies passed here will be added to the final response.

    We use this structure to modify the default response.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus
    headers: Mapping[str, 'NewHeader | HeaderSpec'] | None
    cookies: Mapping[str, 'NewCookie | CookieSpec'] | None

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

    def actionable_headers(self) -> Mapping[str, 'NewHeader'] | None:
        """Returns an optional mapping of headers that should be added."""
        return (  # pyright: ignore[reportReturnType]
            None  # pyrefly: ignore[bad-return]
            if self.headers is None
            else {
                header_name: header
                for header_name, header in self.headers.items()
                if header.is_actionable
            }
        )

    def actionable_cookies(self) -> Mapping[str, 'NewCookie'] | None:
        """Returns an optional mapping of cookies that should be added."""
        return (  # pyright: ignore[reportReturnType]
            None  # pyrefly: ignore[bad-return]
            if self.cookies is None
            else {
                cookie_key: cookie
                for cookie_key, cookie in self.cookies.items()
                if cookie.is_actionable
            }
        )


class ResponseSpecProvider:
    """Base abstract class to provide extra response schemas."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def provide_response_specs(
        cls,
        metadata: 'EndpointMetadata',
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
        parsers: List of instances to be used for this endpoint
            to parse incoming request's body. All instances must be of subtypes
            of :class:`~dmr.parsers.Parser`.
        renderers: List of instances to be used for this endpoint
            to render response's body. All instances must be of subtypes
            of :class:`~dmr.renderers.Renderer`.
        auth: list of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`dmr.security.AsyncAuth`.
            When set it to ``None`` it means that auth
            is disabled for this endpoint.
        no_validate_http_spec: Set of checks that user wants
            to disable for validation in this endpoint.
        allowed_http_methods: Set of extra HTTP methods
            that are allowed for this endpoint.
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
    ``allowed_http_methods`` is used for endpoint definition.
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
    parsers: dict[str, 'Parser']
    renderers: dict[str, 'Renderer']
    auth: list['SyncAuth | AsyncAuth'] | None
    no_validate_http_spec: frozenset['HttpSpec']
    allowed_http_methods: frozenset[str]

    # OpenAPI documentation fields:
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    deprecated: bool = False
    external_docs: 'ExternalDocumentation | None' = None
    callbacks: dict[str, 'Callback | Reference'] | None = None
    servers: list['Server'] | None = None

    def collect_response_specs(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: dict[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        all_responses = []
        for provider in self.response_spec_providers():
            responses = provider.provide_response_specs(
                self,
                controller_cls,
                existing_responses,
            )
            all_responses.extend(responses)
            existing_responses.update({
                response.status_code: response for response in responses
            })
        return all_responses

    def response_spec_providers(self) -> list[type[ResponseSpecProvider]]:
        """
        Determine: from where we should collect response schemas.

        Override this method in your own metadata classes
        if you want more or less response spec providers.

        For example: you can add some custom field to
        :class:`~dmr.controller.Controller` like ``checks=``.
        And you can subclass ``EndpointMetadata``
        to also contain ``checks`` field and override this method
        to also include response specs from this field.
        """
        return [
            *[spec[0] for spec in self.component_parsers],
            *[type(parser) for parser in self.parsers.values()],
            *[type(renderer) for renderer in self.renderers.values()],
            *[type(auth) for auth in (self.auth or [])],
        ]
