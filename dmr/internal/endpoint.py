from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Literal,
    Never,
    TypeAlias,
    final,
    overload,
)

from django.http import HttpRequest, HttpResponseBase
from typing_extensions import ParamSpec, Protocol, Sentinel, TypeVar, deprecated

from dmr.types import EMPTY

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.controller import Controller
    from dmr.cookies import CookieSpec, NewCookie
    from dmr.endpoint import Endpoint
    from dmr.errors import AsyncErrorHandler, SyncErrorHandler
    from dmr.headers import HeaderSpec, NewHeader
    from dmr.internal.context import SerializerContext as SerializerContext
    from dmr.metadata import ResponseSpec
    from dmr.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Link,
        Reference,
        Server,
    )
    from dmr.parsers import Parser
    from dmr.renderers import Renderer
    from dmr.security.base import AsyncAuth, SyncAuth
    from dmr.serializer import BaseSerializer
    from dmr.settings import HttpSpec
    from dmr.throttling import AsyncThrottle, SyncThrottle
    from dmr.validation import (
        ModifyEndpointPayload,
        ValidateEndpointPayload,
    )


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_AnyResponseT = TypeVar(
    '_AnyResponseT',
    bound=HttpResponseBase | Awaitable[HttpResponseBase],
)
_SyncResponseT = TypeVar('_SyncResponseT', bound=HttpResponseBase)
_AsyncResponseT = TypeVar('_AsyncResponseT', bound=Awaitable[HttpResponseBase])

_ThrottlingDef: TypeAlias = (
    Sequence['AsyncThrottle'] | Sequence['SyncThrottle'] | None
)


# Re-exported API:


class ModifySyncCallable(Protocol):
    """
    Type that represents ``@modify`` decorator for sync functions.

    Features:

    - Does not allow using ``HttpResponse`` as the return annotation
    - Does not allow applying the decorator on async endpoints

    """

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _AnyResponseT], /) -> Never: ...

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Sync `error_handler`, `auth` or `throttling` require sync endpoint',
    )
    def __call__(
        self,
        func: Callable[_ParamT, Awaitable[_ReturnT]],
        /,
    ) -> Never: ...

    @overload
    def __call__(
        self,
        func: Callable[_ParamT, _ReturnT],
        /,
    ) -> Callable[_ParamT, _ReturnT]: ...


class ModifyAsyncCallable(Protocol):
    """
    Type that represents ``@modify`` decorator for async functions.

    Features:

    - Does not allow using ``HttpResponse`` as the return annotation
    - Does not allow applying the decorator on sync endpoints

    """

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _AnyResponseT], /) -> Never: ...

    @overload
    def __call__(  # type: ignore[overload-overlap]
        self,
        func: Callable[_ParamT, Awaitable[_ReturnT]],
        /,
    ) -> Callable[_ParamT, _ReturnT]: ...

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Async `error_handler`, `auth` or `throttling` require async endpoint',
    )
    def __call__(
        self,
        func: Callable[_ParamT, _ReturnT],
        /,
    ) -> Never: ...


class ModifyAnyCallable(Protocol):
    """
    Type that represents ``@modify`` decorator for any function.

    Features:

    - Does not allow using ``HttpResponse`` as the return annotation
    - Does not allow specifying sync / async specific parts

    """

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _AnyResponseT], /) -> Never: ...

    @overload
    def __call__(
        self,
        func: Callable[_ParamT, _ReturnT],
        /,
    ) -> Callable[_ParamT, _ReturnT]: ...


_ControllerT = TypeVar('_ControllerT', bound='Controller[BaseSerializer]')
_ModifyDecoratorT = TypeVar(
    '_ModifyDecoratorT',
    bound=ModifyAsyncCallable | ModifySyncCallable | ModifyAnyCallable,
)

# We can't split this line into multiline strings,
# because `pyrefly` does not support this pattern.
_CallableOrClassmethod: TypeAlias = 'Callable[[type[_ControllerT]], _ReturnT] | classmethod[_ControllerT, [], _ReturnT]'  # noqa: E501


@final
@dataclasses.dataclass(frozen=True)
class _ModifyEndpoint:  # we can't use slots here, because docs won't build :(
    """
    Decorator to modify endpoints that return raw model data.

    Apply it to change some API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from dmr import Controller, modify
        >>> from dmr.plugins.pydantic import PydanticFastSerializer

        >>> class TaskController(Controller[PydanticFastSerializer]):
        ...     @modify(status_code=HTTPStatus.ACCEPTED)
        ...     def post(self) -> list[int]:
        ...         return [1, 2]  # id of tasks you have started

    Args:
        status_code: Shows *status_code* in the documentation.
            When *status_code* is passed, always use it by default.
            When not provided, we use smart inference
            based on the HTTP method name for default returned response.
        headers: Shows *headers* in the documentation.
            When *headers* are passed we will
            add them for the default response.
        cookies: Shows *cookies* in the documentation.
            When *cookies* are passed we will add
            them for the default response.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        exclude_validate_responses: Set of status codes that we don't
            validate, even when ``validate_responses`` is enabled.
            Useful for errors like ``500`` that can be raised
            from anywhere and that you might not want to describe.
        semantic_responses: Should semantic responses be collected
            from different providers for this endpoint.
        exclude_semantic_responses: Set of semantic responses status codes
            that user wants to disable.
        validate_events: Should this endpoint validate events?
            If not set, defaults to the ``validate_responses`` value.
            This value only matters if the response
            will be a streaming response that supports event validation.
        extra_responses: List of extra responses
            that this endpoint can return.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this endpoint.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        parsers: Sequence of types to be used for this endpoint
            to parse incoming request's body. All types must be subtypes
            of :class:`~dmr.parsers.Parser`.
        renderers: Sequence of types to be used for this endpoint
            to render response's body. All types must be subtypes
            of :class:`~dmr.renderers.Renderer`.
        validate_negotiation: Should we validate that returned response's
            ``Content-Type`` header matches the one
            that we inferred in the negotiation process?
        auth: Sequence of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`dmr.security.AsyncAuth`.
            Set it to ``None`` to disable auth for this endpoint.
        throttling: Sequence of throttle instances
            to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.throttling.SyncThrottle`.
            Async endpoints must use instances
            of :class:`dmr.throttling.AsyncThrottle`.
            Set it to ``None`` to disable throttling of this endpoint.
        throttling_allow_unsafe_cache: Should this endpoint allow
            unsafe throttle Django cache backends?
        summary: A short summary of what the operation does.
        description: A verbose explanation of the operation behavior.
        tags: A list of tags for API documentation control.
            Used to group operations in OpenAPI documentation.
        operation_id: Unique string used to identify the operation.
        deprecated: Declares this operation to be deprecated.
        external_docs: Additional external documentation for this operation.
        callbacks: A map of possible out-of band callbacks related to the
            parent operation. The key is a unique identifier
            for the Callback Object. Each value in the map
            is a Callback Object that describes
            a request that may be initiated by the API provider and the
            expected responses.
        servers: An alternative servers array to service this operation.
        links: Possible links to other OpenAPI operations.
        response_description: Description for the generated response object.
        ignore_from_spec: If set to ``True``, this endpoint
            would not be added to the final OpenAPI spec.

    Returns:
        The same function with ``__dmr_payload__`` payload instance.

    .. warning::

        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    .. versionchanged:: 0.15.0
        ``modify`` used to be a function, now it is an instance
        with ``lazy`` method for lazy reusable endpoints.

    """

    @overload
    def __call__(  # pyright: ignore[reportOverlappingOverload]
        self,
        *,
        error_handler: None = None,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        extra_responses: list[ResponseSpec] | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[Never] | None = (),
        throttling: Sequence[Never] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        links: dict[str, Link | Reference] | None = None,
        response_description: str | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ModifyAnyCallable: ...

    @overload
    def __call__(
        self,
        *,
        error_handler: AsyncErrorHandler | None = None,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        extra_responses: list[ResponseSpec] | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[AsyncAuth] | None = (),
        throttling: Sequence[AsyncThrottle] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        links: dict[str, Link | Reference] | None = None,
        response_description: str | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ModifyAsyncCallable: ...

    @overload
    def __call__(
        self,
        *,
        error_handler: SyncErrorHandler | None = None,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        extra_responses: list[ResponseSpec] | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[SyncAuth] | None = (),
        throttling: Sequence[SyncThrottle] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        links: dict[str, Link | Reference] | None = None,
        response_description: str | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ModifySyncCallable: ...

    def __call__(  # noqa: WPS211
        self,
        *,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        extra_responses: list[ResponseSpec] | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        error_handler: SyncErrorHandler | AsyncErrorHandler | None = None,
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
        throttling: _ThrottlingDef = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        links: dict[str, Link | Reference] | None = None,
        response_description: str | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ModifyAsyncCallable | ModifySyncCallable | ModifyAnyCallable:
        """Adds the payload to the endpoint function."""
        from dmr.validation import ModifyEndpointPayload  # noqa: PLC0415

        return _add_payload(  # type: ignore[return-value]
            payload=ModifyEndpointPayload(
                status_code=status_code,
                headers=headers,
                cookies=cookies,
                responses=extra_responses,
                validate_responses=validate_responses,
                exclude_validate_responses=exclude_validate_responses,
                semantic_responses=semantic_responses,
                exclude_semantic_responses=exclude_semantic_responses,
                validate_events=validate_events,
                no_validate_http_spec=no_validate_http_spec,
                error_handler=error_handler,
                parsers=parsers,
                renderers=renderers,
                validate_negotiation=validate_negotiation,
                auth=auth,
                throttling=throttling,
                throttling_allow_unsafe_cache=throttling_allow_unsafe_cache,
                summary=summary,
                description=description,
                tags=tags,
                operation_id=operation_id,
                deprecated=deprecated,
                external_docs=external_docs,
                callbacks=callbacks,
                servers=servers,
                links=links,
                response_description=response_description,
                ignore_from_spec=ignore_from_spec,
            ),
        )

    def lazy(
        self,
        provider: _CallableOrClassmethod[_ControllerT, _ModifyDecoratorT],
    ) -> _ModifyDecoratorT:
        """
        Create lazy endpoint for reusable controller definition.

        This provides an agile way to customize all the response details,
        including headers and cookies spec, response status code,
        OpenAPI metadata and other things.

        See :ref:`lazy-reusable-endpoints` for the full example.

        .. versionadded:: 0.15.0
        """

        def factory(controller_cls: type[_ControllerT]) -> Any:
            if isinstance(provider, classmethod):
                return getattr(
                    controller_cls,
                    provider.__name__,
                    provider,
                ).__func__(controller_cls)
            return provider(controller_cls)

        return _add_payload(payload=factory)  # type: ignore[return-value]


modify: Final = _ModifyEndpoint()


class ValidateSyncCallable(Protocol):
    """
    Type that represents ``@validate`` decorator for sync functions.

    Features:

    - Does not allow using anything other
      than ``HttpResponse`` as the return annotation
    - Does not allow applying the decorator on async endpoints

    .. versionadded:: 0.15.0
    """

    # This is a typing-hack to make `@modify` and `@validate` decorators
    # incompatible, so `@validate.lazy(modify_spec)` and vice a versa
    # can't be used in a real code.
    __dmr_fake_marker__: Literal['validate']

    def __call__(  # noqa: D102
        self,
        func: Callable[_ParamT, _SyncResponseT],
        /,
    ) -> Callable[_ParamT, _SyncResponseT]: ...


class ValidateAsyncCallable(Protocol):
    """
    Type that represents ``@validate`` decorator for async functions.

    Features:

    - Does not allow using anything other
        than ``HttpResponse`` as the return annotation
    - Does not allow applying the decorator on sync endpoints

    .. versionadded:: 0.15.0
    """

    __dmr_fake_marker__: Literal['validate']

    def __call__(  # noqa: D102
        self,
        func: Callable[_ParamT, _AsyncResponseT],
        /,
    ) -> Callable[_ParamT, _AsyncResponseT]: ...


class ValidateAnyCallable(Protocol):
    """
    Type that represents ``@modify`` decorator for any function.

    Features:

    - Does not allow using anything other
        than ``HttpResponse`` as the return annotation
    - Does not allow specifying sync / async specific parts

    .. versionadded:: 0.15.0
    """

    __dmr_fake_marker__: Literal['validate']

    def __call__(  # noqa: D102
        self,
        func: Callable[_ParamT, _AnyResponseT],
        /,
    ) -> Callable[_ParamT, _AnyResponseT]: ...


_ValidateDecoratorT = TypeVar(
    '_ValidateDecoratorT',
    bound=ValidateAsyncCallable | ValidateSyncCallable | ValidateAnyCallable,
)


@final
@dataclasses.dataclass(frozen=True)
class _ValidateEndpoint:  # we can't use slots here, because docs won't build :(
    """
    Decorator to validate responses from endpoints that return ``HttpResponse``.

    Apply it to validate important API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django.http import HttpResponse
        >>> from dmr import Controller, validate, ResponseSpec
        >>> from dmr.plugins.pydantic import PydanticFastSerializer

        >>> class TaskController(Controller[PydanticFastSerializer]):
        ...     @validate(
        ...         ResponseSpec(
        ...             return_type=list[int],
        ...             status_code=HTTPStatus.OK,
        ...         ),
        ...     )
        ...     def post(self) -> HttpResponse:
        ...         return HttpResponse(b'[1, 2]', status=HTTPStatus.OK)

    Response validation can be disabled for extra speed
    by sending *validate_responses* falsy parameter
    or by setting this configuration in your ``settings.py`` file:

    .. code-block:: python
        :caption: settings.py

        >>> DMR_SETTINGS = {'validate_responses': False}

    Args:
        response: The main response that this endpoint is allowed to return.
        responses: A collection of other responses that are allowed
            to be returned from this endpoint.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        exclude_validate_responses: Set of status codes that we don't
            validate, even when ``validate_responses`` is enabled.
            Useful for errors like ``500`` that can be raised
            from anywhere and that you might not want to describe.
        semantic_responses: Should semantic responses be collected
            from different providers for this endpoint.
        exclude_semantic_responses: Set of semantic responses status codes
            that user wants to disable.
        validate_events: Should this endpoint validate events?
            If not set, defaults to the ``validate_responses`` value.
            This value only matters if the response
            will be a streaming response that supports event validation.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this endpoint.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        parsers: Sequence of types to be used for this endpoint
            to parse incoming request's body. All types must be subtypes
            of :class:`~dmr.parsers.Parser`.
        renderers: Sequence of types to be used for this endpoint
            to render response's body. All types must be subtypes
            of :class:`~dmr.renderers.Renderer`.
        validate_negotiation: Should we validate that returned response's
            ``Content-Type`` header matches the one
            that we inferred in the negotiation process?
        auth: Sequence of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`dmr.security.AsyncAuth`.
            Set it to ``None`` to disable auth for this endpoint.
        throttling: Sequence of throttle instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`dmr.throttling.SyncThrottle`.
            Async endpoints must use instances
            of :class:`dmr.throttling.AsyncThrottle`.
            Set it to ``None`` to disable throttling of this endpoint.
        throttling_allow_unsafe_cache: Should this controller allow
            unsafe throttle Django cache backends?
        summary: A short summary of what the operation does.
        description: A verbose explanation of the operation behavior.
        tags: A list of tags for API documentation control.
            Used to group operations in OpenAPI documentation.
        operation_id: Unique string used to identify the operation.
        deprecated: Declares this operation to be deprecated.
        external_docs: Additional external documentation for this operation.
        callbacks: A map of possible out-of band callbacks related to the
            parent operation. The key is a unique identifier for the Callback
            Object. Each value in the map is a Callback Object that describes
            a request that may be initiated by the API provider and the
            expected responses.
        servers: An alternative servers array to service this operation.
        ignore_from_spec: If set to ``True``, this endpoint
            would not be added to the final OpenAPI spec.

    Returns:
        The same function with ``__dmr_payload__`` payload instance.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    .. versionchanged:: 0.15.0
        ``validate`` used to be a function, now it is an instance
        with ``lazy`` method for lazy reusable endpoints.

    """

    @overload
    def __call__(
        self,
        response: ResponseSpec,
        /,
        *responses: ResponseSpec,
        error_handler: None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[Never] | None = (),
        throttling: Sequence[Never] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ValidateAnyCallable: ...

    @overload
    def __call__(  # pyright: ignore[reportOverlappingOverload]  # noqa: WPS234
        self,
        response: ResponseSpec,
        /,
        *responses: ResponseSpec,
        error_handler: AsyncErrorHandler | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[AsyncAuth] | None = (),
        throttling: Sequence[AsyncThrottle] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ValidateAsyncCallable: ...

    @overload
    def __call__(
        self,
        response: ResponseSpec,
        /,
        *responses: ResponseSpec,
        error_handler: SyncErrorHandler | None = None,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[SyncAuth] | None = (),
        throttling: Sequence[SyncThrottle] | None = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ValidateSyncCallable: ...

    def __call__(  # noqa: WPS211  # pyright: ignore[reportInconsistentOverload]
        self,
        response: ResponseSpec,
        /,
        *responses: ResponseSpec,
        validate_responses: bool | None = None,
        exclude_validate_responses: Set[HTTPStatus] | None = frozenset(),
        semantic_responses: bool | None = None,
        exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
        validate_events: bool | None = None,
        no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
        error_handler: SyncErrorHandler | AsyncErrorHandler | None = None,
        parsers: Sequence[Parser] | None = None,
        renderers: Sequence[Renderer] | None = None,
        validate_negotiation: bool | None = None,
        auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
        throttling: _ThrottlingDef = (),
        throttling_allow_unsafe_cache: bool | Sentinel | None = EMPTY,
        summary: _StrOrPromise | None = None,
        description: _StrOrPromise | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        deprecated: bool = False,
        external_docs: ExternalDocumentation | None = None,
        callbacks: dict[str, Callback | Reference] | None = None,
        servers: list[Server] | None = None,
        ignore_from_spec: bool | None = None,
    ) -> ValidateAnyCallable | ValidateAsyncCallable | ValidateSyncCallable:
        """Adds the payload to the endpoint function."""
        from dmr.validation import ValidateEndpointPayload  # noqa: PLC0415

        return _add_payload(  # type: ignore[return-value]
            payload=ValidateEndpointPayload(
                responses=[response, *responses],
                validate_responses=validate_responses,
                exclude_validate_responses=exclude_validate_responses,
                semantic_responses=semantic_responses,
                exclude_semantic_responses=exclude_semantic_responses,
                validate_events=validate_events,
                no_validate_http_spec=no_validate_http_spec,
                error_handler=error_handler,
                parsers=parsers,
                renderers=renderers,
                validate_negotiation=validate_negotiation,
                auth=auth,
                throttling=throttling,
                throttling_allow_unsafe_cache=throttling_allow_unsafe_cache,
                summary=summary,
                description=description,
                tags=tags,
                operation_id=operation_id,
                deprecated=deprecated,
                external_docs=external_docs,
                callbacks=callbacks,
                servers=servers,
                ignore_from_spec=ignore_from_spec,
            ),
        )

    def lazy(
        self,
        provider: _CallableOrClassmethod[_ControllerT, _ValidateDecoratorT],
    ) -> _ValidateDecoratorT:
        """
        Create lazy endpoint for reusable controller definition.

        This provides an agile way to customize all the response details,
        including headers and cookies spec, response status code,
        OpenAPI metadata and other things.

        See :ref:`lazy-reusable-endpoints` for the full example.

        .. versionadded:: 0.15.0
        """
        return _lazy_payload(provider)


validate: Final = _ValidateEndpoint()


@overload
def request_endpoint(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> Endpoint: ...


@overload
def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> Endpoint | None: ...


def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> Endpoint | None:
    """
    Return an instance of the ``Endpoint`` that was used for this request.

    When *strict* is passed and *request* has no endpoint,
    we raise :exc:`AttributeError`.
    This can happen for ``405`` responses, for example.
    They don't have endpoints. All others do.

    .. versionadded:: 0.7.0
    """
    endpoint = getattr(request, '__dmr_endpoint__', None)
    if endpoint is None and strict:
        raise AttributeError('__dmr_endpoint__')
    return endpoint


# Internal API:


def _lazy_payload(
    provider: _CallableOrClassmethod[_ControllerT, _ReturnT],
) -> _ReturnT:
    def factory(controller_cls: type[_ControllerT]) -> Any:
        if isinstance(provider, classmethod):
            return getattr(
                controller_cls,
                provider.__name__,
                provider,
            ).__func__(controller_cls)
        return provider(controller_cls)

    return _add_payload(payload=factory)  # type: ignore[return-value]


def _add_payload(
    *,
    payload: (
        ModifyEndpointPayload
        | ValidateEndpointPayload
        | Callable[[type[_ControllerT]], Any]
    ),
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # Add payload for future use in the Endpoint creation.
    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        func.__dmr_payload__ = payload  # type: ignore[attr-defined]
        return func

    return decorator
