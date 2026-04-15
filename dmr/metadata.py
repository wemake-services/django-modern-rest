import dataclasses
import typing as ty
from abc import abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Mapping, Set
from http import HTTPStatus
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Final,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from dmr.components import ComponentParser
    from dmr.controller import Controller
    from dmr.cookies import CookieSpec, NewCookie
    from dmr.errors import AsyncErrorHandler, SyncErrorHandler
    from dmr.headers import HeaderSpec, NewHeader
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Link,
        Reference,
        Response,
        Server,
    )
    from dmr.parsers import Parser
    from dmr.renderers import Renderer
    from dmr.security.base import AsyncAuth, SyncAuth
    from dmr.serializer import BaseSerializer
    from dmr.settings import HttpSpec
    from dmr.throttling import AsyncThrottle, SyncThrottle

ComponentParserSpec: TypeAlias = tuple['ComponentParser', Any, tuple[Any, ...]]


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
        streaming: Are we working with the stream response?
        limit_to_content_types: This response can only happen
            only for given content types. By default, when equals to ``None``,
            all responses can happen for all content types.
        description: Text comment about what this response represents.
        links: Possible links to other OpenAPI operations.

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
    limit_to_content_types: Set[str] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    streaming: bool = dataclasses.field(
        kw_only=True,
        default=False,
    )

    # Metadata:
    description: str | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    links: dict[str, 'Link | Reference'] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )

    def __post_init__(self) -> None:
        """If headers and cookies are not set, look for metadata and use it."""
        metadata = get_annotated_metadata(
            self.return_type,
            None,
            ResponseSpecMetadata,
        )
        if metadata is not None:
            object.__setattr__(
                self,
                'headers',
                {**(metadata.headers or {}), **(self.headers or {})},
            )
            object.__setattr__(
                self,
                'cookies',
                {**(metadata.cookies or {}), **(self.cookies or {})},
            )

    def get_schema(
        self,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> 'Response':
        """
        Returns the OpenAPI schema for the response.

        Can be customized in subclasses.
        Be careful when overriding the schema generation.
        We don't provide any validations for the returned schema.
        Ensure that it is in sync with the actual response.
        """
        item_schema = (
            self.streaming and context.config.openapi_version_info >= (3, 2)
        )
        return context.generators.response.get_schema(
            self,
            metadata,
            serializer,
            context,
            schema_field_name='item_schema' if item_schema else 'schema',
            # Despite the fact that it looks like a response,
            # produced stream events are not regular responses.
            used_for_response=not item_schema,
        )


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class ResponseSpecMetadata:
    """
    Special type to be used in ``Annotate`` to provide header and cookie specs.

    Attributes:
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response.
        cookies: Shows *cookies* in the documentation.
            When passed, we validate that all given required cookies are present
            in the final response.

    .. versionadded:: 0.7.0
    """

    headers: Mapping[str, 'HeaderSpec'] | None = dataclasses.field(
        kw_only=True,
        default=None,
        hash=False,
    )
    cookies: Mapping[str, 'CookieSpec'] | None = dataclasses.field(
        kw_only=True,
        default=None,
        hash=False,
    )


_ASYNC_ITERATOR_TYPES: Final = frozenset((
    AsyncGenerator,
    AsyncIterator,
    ty.AsyncIterator,
    ty.AsyncGenerator,
))


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
        streaming: Are we working with the stream response?
        description: Text comment about what this response represents.
        links: Possible links to other OpenAPI operations.

    We use this structure to modify the default response.
    """

    # Class-level API:
    response_spec_cls: ClassVar[type[ResponseSpec]] = ResponseSpec

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus
    headers: Mapping[str, 'NewHeader | HeaderSpec'] | None
    cookies: Mapping[str, 'NewCookie | CookieSpec'] | None
    streaming: bool

    # Metadata:
    description: str | None
    links: dict[str, 'Link | Reference'] | None

    def to_spec(self) -> ResponseSpec:
        """Convert response modification to response description."""
        return self.response_spec_cls(
            return_type=self.infer_return_type(),
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
            streaming=self.streaming,
            # Metadata:
            description=self.description,
            links=self.links,
        )

    def infer_return_type(self) -> Any:
        """Infers return type if it needs some extra love."""
        from dmr.exceptions import UnsolvableAnnotationsError  # noqa: PLC0415

        if self.streaming:
            origin = get_origin(self.return_type)
            type_args = get_args(self.return_type)
            if type_args and origin in _ASYNC_ITERATOR_TYPES:
                return type_args[0]
            raise UnsolvableAnnotationsError(
                'Cannot infer streaming item annotation from '
                f'{self.return_type}, we require the return type to be '
                'AsyncIterator or AsyncGenerator',
            )

        return self.return_type

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

    def build_headers(
        self,
        renderer: 'Renderer',
    ) -> dict[str, str]:
        """Returns headers with values for raw data endpoints."""
        result_headers: dict[str, Any] = {'Content-Type': renderer.content_type}
        headers = self.actionable_headers()
        if not headers:
            return result_headers
        result_headers.update({
            header_name: response_header.value
            for header_name, response_header in headers.items()
        })
        return result_headers


class ResponseSpecProvider:
    """Base abstract class to provide extra response schemas."""

    __slots__ = ()

    @abstractmethod
    def provide_response_specs(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """
        Provide custom response specs.

        Will be called to inject response specs from different components
        into the resulting endpoint metadata.
        """
        raise NotImplementedError

    def _add_new_response(
        self,
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
        endpoint_name: Text representation of an endpoint
            name for better error messages.
        type_annotations: Unmodified unnotations of the endpoint function,
            returned by the resolution method.
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
        throttling: Sequence of throttle instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.throttling.SyncThrottle`.
            Async endpoints must use instances
            of :class:`dmr.throttling.AsyncThrottle`.
            Set it to ``None`` to disable throttling of this endpoint.
        no_validate_http_spec: Set of checks that user wants
            to disable for validation in this endpoint.
        allowed_http_methods: Set of extra HTTP methods
            that are allowed for this endpoint.
        semantic_responses: Should semantic responses
            from different providers be collected?
        exclude_semantic_responses: Set of semantic responses
            that user wants to disable.
        validate_events: Should this endpoint validate events?
            If not set, defaults to the ``validate_responses`` value.
            This value only matters if the response
            will be a streaming response that supports event validation.
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

    endpoint_name: str
    type_annotations: dict[str, Any]
    responses: dict[HTTPStatus, ResponseSpec]
    validate_responses: bool | None
    method: str
    modification: ResponseModification | None
    error_handler: 'SyncErrorHandler | AsyncErrorHandler | None'
    component_parsers: list[ComponentParserSpec]
    parsers: dict[str, 'Parser']
    renderers: dict[str, 'Renderer']
    auth: list['SyncAuth | AsyncAuth'] | None

    # First line of throttling:
    throttling_before_auth: tuple['SyncThrottle | AsyncThrottle', ...] | None
    # Second line of throttling:
    throttling_after_auth: tuple['SyncThrottle | AsyncThrottle', ...] | None

    no_validate_http_spec: frozenset['HttpSpec']
    allowed_http_methods: frozenset[str]
    semantic_responses: bool
    exclude_semantic_responses: frozenset[HTTPStatus]
    validate_events: bool

    # OpenAPI documentation fields:
    summary: str | None
    description: str | None
    tags: list[str] | None
    operation_id: str | None
    deprecated: bool
    external_docs: 'ExternalDocumentation | None'
    callbacks: dict[str, 'Callback | Reference'] | None
    servers: list['Server'] | None

    # Pre-computed fields:
    throttling: tuple['SyncThrottle | AsyncThrottle', ...] | None = (
        dataclasses.field(init=False)
    )

    def __post_init__(self) -> None:
        """Set pre-computed fields."""
        # Combine throttling into a single element for convenience:
        object.__setattr__(
            self,
            'throttling',
            (
                (self.throttling_before_auth or ())
                + (self.throttling_after_auth or ())
            )
            or None,
        )

    def collect_response_specs(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: dict[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Collect unique responses for all possible response providers."""
        all_responses: list[ResponseSpec] = []
        for provider in self.response_spec_providers():
            responses = provider.provide_response_specs(
                self,
                controller_cls,
                existing_responses,
            )
            responses = [
                response
                for response in responses
                if response.status_code not in self.exclude_semantic_responses
            ]
            all_responses.extend(responses)
            existing_responses.update({
                response.status_code: response for response in responses
            })

        # We we have stream renderers, we know that they can't be used
        # for error responses, so we will limit error responses
        # to be only returned by non-stream ones.
        # If there are no stream renderers, nothing will happen.
        non_streaming_renderers = {
            renderer.content_type
            for renderer in self.renderers.values()
            if not renderer.streaming
        }
        # Do not limit anything, if there are no stream renderers:
        return [
            dataclasses.replace(
                response,
                limit_to_content_types=(
                    None
                    if len(non_streaming_renderers) == len(self.renderers)
                    else non_streaming_renderers
                ),
            )
            for response in all_responses
        ]

    def response_spec_providers(self) -> list[ResponseSpecProvider]:
        """
        Determine: from where we should collect response schemas.

        Override this method in your own metadata classes
        if you want more or less response spec providers.

        For example: you can add some custom field to
        :class:`~dmr.controller.Controller` like ``checks=``.
        And you can subclass ``EndpointMetadata``
        to also contain ``checks`` field and override this method
        to also include response specs from this field.

        Define ``semantic_responses`` to ``False`` on settings
        or controller level to disable semantic responses collection.
        """
        if not self.semantic_responses:
            return []

        return [
            *[spec[0] for spec in self.component_parsers],
            *self.parsers.values(),
            *self.renderers.values(),
            *(self.auth or []),
            *(self.throttling_before_auth or []),
            *(self.throttling_after_auth or []),
        ]


_MetadataT = TypeVar('_MetadataT')


def get_annotated_metadata(
    model: Any,
    model_meta: tuple[Any, ...] | None,
    metadata_type: type[_MetadataT],
) -> _MetadataT | None:
    """
    Find given *metadata_type* in :attr:`typing.Annotate.__metadata__`.

    Or return ``None`` if it can't be found.
    """
    if get_origin(model) is Annotated and model.__metadata__:
        for metadata in model.__metadata__:
            if isinstance(metadata, metadata_type):
                return metadata

    for metadata in model_meta or ():
        if isinstance(metadata, metadata_type):
            return metadata
    return None
