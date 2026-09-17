import dataclasses
import functools
import typing as ty
from abc import abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Mapping, Set
from http import HTTPStatus
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Generic,
    Self,
    TypeAlias,
    get_args,
    get_origin,
)

from typing_extensions import TypeVar, override

from dmr.internal.types import (
    find_annotated_metadata,
    iter_union_members,
)

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

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

_SpecT = TypeVar('_SpecT', 'HeaderSpec', 'CookieSpec')


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
    description: '_StrOrPromise | None' = dataclasses.field(
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
        controller_cls: type['Controller[BaseSerializer]'],
        context: 'OpenAPIContext',
    ) -> 'Response':
        """
        Returns the OpenAPI schema for the response.

        Can be customized in subclasses.
        Be careful when overriding the schema generation.
        We don't provide any validations for the returned schema.
        Ensure that it is in sync with the actual response.

        .. versionchanged:: 0.16.0
            Now accepts *controller_cls* parameter instead of *serializer*.

        """
        item_schema = (
            self.streaming and context.config.openapi_version_info >= (3, 2)
        )
        return context.generators.response.get_schema(
            self,
            metadata,
            controller_cls,
            context,
            schema_field_name='item_schema' if item_schema else 'schema',
            # Despite the fact that it looks like a response,
            # produced stream events are not regular responses.
            used_for_response=not item_schema,
        )


class MergeableMetadata:
    """
    Base for ``Annotated`` metadata that survives union types.

    A union is a single response or a single parsed model,
    but each of its members can carry its own metadata.
    Subclasses define what the metadata of the whole union is.

    Metadata types that don't subclass this are only looked up
    on the annotation itself, never on union members:
    there is no meaningful way to combine them.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    @classmethod
    def merge(
        cls,
        first: Any,
        second: Any,
    ) -> 'Self | None':
        """
        Combine metadata of two members of the same union.

        Both arguments are instances of this class or ``None``,
        which means that this member carries no metadata at all.
        That is still information about the union: such a member
        is a response without whatever the other member declares.
        Subclasses type the arguments as their own type,
        which is why they are ``Any`` here.

        Must not depend on the order of the arguments,
        union members are merged one by one.
        """
        raise NotImplementedError

    @classmethod
    def from_union(cls, annotation: Any) -> 'Self | None':
        """Find and merge this metadata across all members of a union."""
        return functools.reduce(
            cls.merge,
            [
                find_annotated_metadata(member, cls)
                for member in iter_union_members(annotation)
            ],
        )


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class ResponseSpecMetadata(MergeableMetadata):
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

    .. versionchanged:: 0.16.0
        Can now be used on members of a union return type,
        see :meth:`merge`.

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

    @classmethod
    @override
    def merge(
        cls,
        first: 'ResponseSpecMetadata | None',
        second: 'ResponseSpecMetadata | None',
    ) -> 'ResponseSpecMetadata | None':
        """
        Combine metadata of two members of the same union return type.

        Annotating a member describes that member only:
        ``Annotated[User, meta] | str`` says that ``User`` responses
        carry the headers and cookies from *meta*, while ``str``
        responses do not. A single response has a single set of specs,
        so the result keeps everything both members declare, but marks
        a spec as ``required=False`` unless every member provides it.

        Annotate the whole union instead
        - ``Annotated[User | str, meta]`` - to require it everywhere.
        """
        if first is None and second is None:
            return None
        empty = cls()
        first = empty if first is None else first
        second = empty if second is None else second
        return cls(
            headers=cls._merge_specs(first.headers, second.headers),
            cookies=cls._merge_specs(first.cookies, second.cookies),
        )

    @classmethod
    def _merge_specs(
        cls,
        first: Mapping[str, _SpecT] | None,
        second: Mapping[str, _SpecT] | None,
    ) -> dict[str, _SpecT]:
        left = first or {}
        right = second or {}
        # The left side wins for specs that both members declare:
        return {
            name: dataclasses.replace(
                spec,
                required=cls._required_in_both(name, left, right),
            )
            for name, spec in {**right, **left}.items()
        }

    @classmethod
    def _required_in_both(
        cls,
        name: str,
        left: Mapping[str, _SpecT],
        right: Mapping[str, _SpecT],
    ) -> bool:
        """A spec is only required when both merged members require it."""
        return all(
            name in specs and specs[name].required for specs in (left, right)
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

    .. versionchanged:: 0.16.0
        Removed several methods like ``actionable_headers()``,
        ``actionable_cookies()``, ``infer_return_type()``, ``build_headers()``.
        Added ``actionable_headers`` and ``actionable_cookies``
        pre-computed attributes.

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
    description: '_StrOrPromise | None'
    links: dict[str, 'Link | Reference'] | None

    # Pre-computed fields:
    actionable_headers: Mapping[str, str] | None = dataclasses.field(
        init=False,
    )
    actionable_cookies: Mapping[str, 'NewCookie'] | None = dataclasses.field(
        init=False,
    )

    def __post_init__(self) -> None:
        """Create pre-computed fields."""
        object.__setattr__(
            self,
            'actionable_headers',
            self._actionable_headers(),
        )
        object.__setattr__(
            self,
            'actionable_cookies',
            self._actionable_cookies(),
        )

    def to_spec(self) -> ResponseSpec:
        """Convert response modification to response description."""
        return self.response_spec_cls(
            return_type=self._infer_return_type(),
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

    def _infer_return_type(self) -> Any:
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

    def _actionable_headers(self) -> Mapping[str, str] | None:
        """Returns an optional mapping of headers that should be added."""
        return (  # pyright: ignore[reportUnknownVariableType]
            None
            if self.headers is None
            else {
                header_name: header.value  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]  # pyrefly: ignore[missing-attribute]
                for header_name, header in self.headers.items()
                if header.is_actionable
            }
        )

    def _actionable_cookies(self) -> Mapping[str, 'NewCookie'] | None:
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


_AuthT = TypeVar(
    '_AuthT',
    bound='SyncAuth | AsyncAuth',
    default='SyncAuth | AsyncAuth',
)
_ThrottlingT = TypeVar(
    '_ThrottlingT',
    bound='SyncThrottle | AsyncThrottle',
    default='SyncThrottle | AsyncThrottle',
)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata(Generic[_AuthT, _ThrottlingT]):
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
            of responses for this endpoint? Already resolved from
            the global setting, the controller, and the endpoint.
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
        validate_negotiation: Should we validate that returned response's
            ``Content-Type`` header matches the one
            that we inferred in the negotiation process?
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
        throttling_before_auth: Sequence of throttle instances
            to be used before auth checks.
        throttling_after_auth: Sequence of throttle instances
            to be used after auth checks.
        throttling_allow_unsafe_cache: Should this endpoint allow
            unsafe throttle Django cache backends?
        exclude_validate_responses: Set of status codes that we don't
            validate, even when ``validate_responses`` is enabled.
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
            Controller-level tags are already included here,
            router-level ones are added during the schema generation.
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
        ignore_from_spec: If set to ``True``, this endpoint
            would not be added to the final OpenAPI spec.

    ``method`` can be a custom name, not specified
    in :class:`http.HTTPMethod` enum, when
    ``allowed_http_methods`` is used for endpoint definition.
    This might be useful for cases like when you need
    to define a method like ``query``, which is not yet formally accepted.
    Or provide domain specific HTTP methods.

    .. seealso::

        https://www.ietf.org/archive/id/draft-ietf-httpbis-safe-method-w-body-05.html

    """

    endpoint_name: str
    type_annotations: dict[str, Any]
    responses: dict[HTTPStatus, ResponseSpec]
    validate_responses: bool
    method: str
    modification: ResponseModification | None
    error_handler: 'SyncErrorHandler | AsyncErrorHandler | None'
    component_parsers: list[ComponentParserSpec]
    parsers: dict[str, 'Parser']
    renderers: dict[str, 'Renderer']
    validate_negotiation: bool
    auth: list[_AuthT] | None

    # First line of throttling:
    throttling_before_auth: tuple[_ThrottlingT, ...] | None
    # Second line of throttling:
    throttling_after_auth: tuple[_ThrottlingT, ...] | None
    throttling_allow_unsafe_cache: bool | None

    exclude_validate_responses: frozenset[HTTPStatus]
    no_validate_http_spec: frozenset['HttpSpec']
    allowed_http_methods: frozenset[str]
    semantic_responses: bool
    exclude_semantic_responses: frozenset[HTTPStatus]
    validate_events: bool

    # OpenAPI documentation fields:
    summary: '_StrOrPromise | None'
    description: '_StrOrPromise | None'
    tags: list[str] | None
    operation_id: str | None
    deprecated: bool
    external_docs: 'ExternalDocumentation | None'
    callbacks: dict[str, 'Callback | Reference'] | None
    servers: list['Server'] | None
    ignore_from_spec: bool

    # Pre-computed fields:
    throttling: tuple[_ThrottlingT, ...] | None = dataclasses.field(init=False)

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
        for provider in self.semantic_schema_providers(controller_cls):
            responses = provider.provide_response_specs(
                self,  # type: ignore[arg-type]
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

    def semantic_schema_providers(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[ResponseSpecProvider]:
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
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        if not self.semantic_responses:
            return []

        return [
            *[spec[0] for spec in self.component_parsers],
            *self.parsers.values(),
            *self.renderers.values(),
            *(self.auth or []),
            *(self.throttling_before_auth or []),
            *(self.throttling_after_auth or []),
            # Default providers, must be last:
            *resolve_setting(Settings.semantic_schema_providers),
        ]


_MetadataT = TypeVar('_MetadataT')


def get_annotated_metadata(
    model: Any,
    metadata_type: type[_MetadataT],
    *,
    model_meta: tuple[Any, ...] | None = None,
) -> _MetadataT | None:
    """
    Find given *metadata_type* in *model*.

    *model* can be :data:`typing.Annotated` object.
    Or it can be a regular model, with *model_meta*,
    which is the ``__metadata__`` field from ``Annotated``.

    Type aliases are unwrapped on the way,
    both ``X: TypeAlias = Annotated[...]`` and ``type X = Annotated[...]``
    are looked through, including aliases of aliases
    and subscripted generic aliases.

    When *model* is a union and *metadata_type*
    is a :class:`MergeableMetadata` subclass, metadata of all union members
    is merged by that type. Other metadata types are not looked
    for on union members at all.

    Or return ``None`` if nothing can be found.

    .. versionchanged:: 0.16.0
        Type aliases and union members are now inspected.

    """
    metadata = find_annotated_metadata(model, metadata_type)
    if metadata is not None:
        return metadata

    for model_metadata in model_meta or ():
        if isinstance(model_metadata, metadata_type):
            return model_metadata

    if issubclass(metadata_type, MergeableMetadata):
        # `issubclass` does not narrow `type[_MetadataT]` for all checkers:
        return metadata_type.from_union(model)  # pyrefly: ignore[bad-return]
    return None
