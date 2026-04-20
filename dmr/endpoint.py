import asyncio
import inspect
import threading
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, overload

from django.http import HttpResponse, HttpResponseBase
from django.urls import URLPattern
from typing_extensions import ParamSpec, TypeVar

from dmr.cookies import CookieSpec, NewCookie
from dmr.errors import AsyncErrorHandler, SyncErrorHandler
from dmr.exceptions import (
    DataRenderingError,
    InternalServerError,
    NotAuthenticatedError,
    ResponseSchemaError,
    ValidationError,
)
from dmr.headers import HeaderSpec, NewHeader
from dmr.internal.context import SerializerContext as SerializerContext
from dmr.internal.endpoint import (
    ModifyAnyCallable,
    ModifyAsyncCallable,
    ModifySyncCallable,
)
from dmr.internal.endpoint import (
    request_endpoint as request_endpoint,
)
from dmr.metadata import EndpointMetadata, ResponseModification, ResponseSpec
from dmr.negotiation import RequestNegotiator, ResponseNegotiator
from dmr.openapi.objects import (
    Callback,
    ExternalDocumentation,
    Link,
    Operation,
    Reference,
    Server,
)
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.response import APIError, RedirectTo
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import HttpSpec, Settings, resolve_setting
from dmr.throttling import AsyncThrottle, SyncThrottle
from dmr.validation import (
    EndpointMetadataBuilder,
    EndpointMetadataValidator,
    ModifyEndpointPayload,
    Payload,
    ResponseValidator,
    ValidateEndpointPayload,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.routing import Router
    from dmr.validation.response import ValidatedModification


class Endpoint:  # noqa: WPS214
    """
    Represents the single API endpoint.

    Is built during the import time.
    In the runtime only does response validate, which can be disabled.
    """

    __slots__ = (
        '_async_lock',
        '_func',
        '_serializer_context',
        '_sync_lock',
        'is_async',
        'metadata',
        'request_negotiator',
        'response_negotiator',
        'response_validator',
    )

    # Instance API:
    _func: Callable[..., Any]

    # Class API:
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        SerializerContext
    )
    metadata_builder_cls: ClassVar[type[EndpointMetadataBuilder]] = (
        EndpointMetadataBuilder
    )
    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        EndpointMetadataValidator
    )
    metadata_cls: ClassVar[type[EndpointMetadata]] = EndpointMetadata
    response_modification_cls: ClassVar[type[ResponseModification]] = (
        ResponseModification
    )
    request_negotiator_cls: ClassVar[type[RequestNegotiator]] = (
        RequestNegotiator
    )
    response_negotiator_cls: ClassVar[type[ResponseNegotiator]] = (
        ResponseNegotiator
    )
    response_validator_cls: ClassVar[type[ResponseValidator]] = (
        ResponseValidator
    )

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """
        Create an entrypoint.

        Args:
            func: Entrypoint handler. An actual function to be called.
            controller_cls: ``Controller`` class that this endpoint belongs to.

        .. danger::

            Endpoint object must **not** have any mutable instance state,
            because its instance is reused for all requests.
            It is fine to have common locks for throttling, because
            this way we guard cache concurrent access
            from different thread / coroutines.

        """
        type_annotations = controller_cls.annotations_context(func)
        self._serializer_context = self.serializer_context_cls(
            func,
            controller_cls,
            type_annotations,
        )
        # We need to add payloads to functions that don't have it,
        # since decorator is optional:
        payload: Payload = getattr(func, '__dmr_payload__', None)
        # We add metadata in two steps:
        # 1. We construct metadata with no responses yet.
        #    We only do basic validation at this point: structure, types, etc.
        #    No semantics validation / etc.
        # 2. When metadata is ready, we collect all the responses from all
        #    of the components that support it. Including custom ones.
        #    Then we enrich metadata with collected responses and use it.
        # Done!
        metadata = self.metadata_builder_cls(
            payload=payload,
            controller_cls=controller_cls,
            func=func,
            metadata_cls=self.metadata_cls,
            response_modification_cls=self.response_modification_cls,
            component_parsers=self._serializer_context.component_parsers,
            type_annotations=type_annotations,
        )()
        self.metadata_validator_cls(metadata=metadata)(
            func,
            payload=payload,
            controller_cls=controller_cls,
        )
        func.__metadata__ = metadata  # type: ignore[attr-defined]
        self.metadata = metadata
        self.request_negotiator = self.request_negotiator_cls(
            self.metadata,
            controller_cls.serializer,
        )
        self.response_negotiator = self.response_negotiator_cls(
            self.metadata,
            controller_cls.serializer,
            streaming=controller_cls.streaming,
        )

        # We need a func before any wrappers, but with metadata:
        self.response_validator = self.response_validator_cls(
            metadata,
            controller_cls.serializer,
        )
        # We can now run endpoint's optimization:
        controller_cls.serializer.optimizer.optimize_endpoint(metadata)

        # Locks:
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

        # Now we can add wrappers:
        if inspect.iscoroutinefunction(func):
            self.is_async = True
            self._func = self._async_endpoint(func)
        else:
            self.is_async = False
            self._func = self._sync_endpoint(func)

    def __call__(
        self,
        controller: 'Controller[BaseSerializer]',
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """Run the endpoint and return the response."""
        return self._func(  # type: ignore[no-any-return]
            controller,
            *args,
            **kwargs,
        )

    def handle_error(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponseBase:
        """
        Return error response if possible.

        Override this method to add custom error handling.
        """
        # NOTE: if you change something here,
        # also change in `handle_async_error`
        if self.metadata.error_handler is not None:
            try:
                # We validate this, no error possible in runtime:
                return self.metadata.error_handler(  # type: ignore[return-value]
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return controller.handle_error(
                self,
                controller,
                exc,
            )
        except Exception:
            # And the last option is to handle error globally:
            return self._global_error_handler(controller, exc)

    async def handle_async_error(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Return error response if possible.

        Override this method to add custom async error handling.
        """
        # NOTE: if you change something here, also change in `handle_error`
        if self.metadata.error_handler is not None:
            try:
                # We validate this, no error possible in runtime:
                return await self.metadata.error_handler(  # type: ignore[no-any-return, misc]
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return await controller.handle_async_error(
                self,
                controller,
                exc,
            )
        except Exception:
            # And the last option is to handle error globally:
            return self._global_error_handler(controller, exc)

    def get_schema(
        self,
        path: str,
        pattern: URLPattern,
        controller_name: str,
        serializer: type[BaseSerializer],
        context: 'OpenAPIContext',
        router: 'Router',
    ) -> Operation:
        """Build an OpenAPI Operation from an endpoint."""
        operation_id = self.get_operation_id(
            path,
            controller_name,
            serializer,
            context,
        )
        request_body, params_list = context.generators.component_parsers(
            operation_id,
            pattern,
            self.metadata,
            serializer,
        )
        security = context.generators.security_scheme(
            self.metadata.auth,
            serializer,
        )

        tags = [
            *router.tags,
            *(self.metadata.tags or []),
        ]

        return Operation(
            tags=tags or None,
            summary=self.metadata.summary,
            description=self.metadata.description,
            deprecated=self.metadata.deprecated or router.deprecated,
            security=security,
            external_docs=self.metadata.external_docs,
            servers=self.metadata.servers,
            callbacks=self.metadata.callbacks,
            operation_id=operation_id,
            request_body=request_body,
            responses=context.generators.response(self.metadata, serializer),
            parameters=params_list,
        )

    def get_operation_id(
        self,
        path: str,
        controller_name: str,
        serializer: type[BaseSerializer],
        context: 'OpenAPIContext',
    ) -> str:
        """Customize how OperationId is generated for the OpenAPI."""
        return context.generators.operation_id(
            path,
            controller_name,
            self.metadata,
            serializer,
        )

    def _async_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Awaitable[HttpResponseBase]]:
        # NOTE: if you change something here, also change in `_sync_endpoint`
        @wraps(func)
        async def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            try:  # noqa: WPS229
                controller.request.__dmr_endpoint__ = self  # type: ignore[attr-defined]

                # Run checks:
                await self._run_async_checks(controller)

                # Parse request:
                context = self._serializer_context(self, controller)

                # Return response:
                func_result = await func(controller, **context)
            except (APIError, RedirectTo) as exc:
                func_result = controller.to_error(
                    exc.raw_data,
                    status_code=exc.status_code,
                    headers=exc.headers,
                    cookies=getattr(exc, 'cookies', None),
                    renderer=getattr(exc, 'renderer', None),
                )
            except Exception as exc:
                func_result = await self.handle_async_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., HttpResponseBase]:
        # NOTE: if you change something here, also change in `_async_endpoint`
        @wraps(func)
        def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            try:  # noqa: WPS229
                controller.request.__dmr_endpoint__ = self  # type: ignore[attr-defined]

                # Run checks:
                self._run_checks(controller)

                # Parse request:
                context = self._serializer_context(self, controller)

                # Return response:
                func_result = func(controller, **context)
            except (APIError, RedirectTo) as exc:
                func_result = controller.to_error(
                    exc.raw_data,
                    status_code=exc.status_code,
                    headers=exc.headers,
                    cookies=getattr(exc, 'cookies', None),
                    renderer=getattr(exc, 'renderer', None),
                )
            except Exception as exc:
                func_result = self.handle_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    # Sync checks:

    def _run_checks(self, controller: 'Controller[BaseSerializer]') -> None:
        # First round of throttling:
        self._run_throttle_before(controller)
        # Negotiate response:
        self.response_negotiator(controller.request)
        # Auth:
        self._run_auth(controller)
        # Second round of throttling:
        self._run_throttle_after(controller)

    def _run_throttle_before(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_before_auth is None:
            return
        for throttle in self.metadata.throttling_before_auth:
            assert isinstance(throttle, SyncThrottle)  # noqa: S101
            with self._sync_lock:
                throttle(self, controller)

    def _run_auth(self, controller: 'Controller[BaseSerializer]') -> None:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, SyncAuth)  # noqa: S101
            authed_by = auth(self, controller)
            if authed_by is not None:
                controller.request.__dmr_auth__ = authed_by  # type: ignore[attr-defined]
                return
        raise NotAuthenticatedError

    def _run_throttle_after(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_after_auth is None:
            return
        for throttle in self.metadata.throttling_after_auth:
            assert isinstance(throttle, SyncThrottle)  # noqa: S101
            with self._sync_lock:
                throttle(self, controller)

    # Async checks:

    async def _run_async_checks(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        # First round of throttling:
        await self._run_async_throttle_before(controller)
        # Negotiate response:
        self.response_negotiator(controller.request)
        # Auth:
        await self._run_async_auth(controller)
        # Second round of throttling:
        await self._run_async_throttle_after(controller)

    async def _run_async_throttle_before(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_before_auth is None:
            return
        for throttle in self.metadata.throttling_before_auth:
            assert isinstance(throttle, AsyncThrottle)  # noqa: S101
            # We have to check them in sync one by one :(
            async with self._async_lock:
                await throttle(self, controller)  # noqa: WPS476

    async def _run_async_auth(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, AsyncAuth)  # noqa: S101
            authed_by = await auth(self, controller)  # noqa: WPS476
            if authed_by is not None:
                controller.request.__dmr_auth__ = authed_by  # type: ignore[attr-defined]
                return
        raise NotAuthenticatedError

    async def _run_async_throttle_after(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_after_auth is None:
            return
        for throttle in self.metadata.throttling_after_auth:
            assert isinstance(throttle, AsyncThrottle)  # noqa: S101
            # We have to check them in sync one by one :(
            async with self._async_lock:
                await throttle(self, controller)  # noqa: WPS476

    # Utils:

    def _make_http_response(
        self,
        controller: 'Controller[BaseSerializer]',
        raw_data: Any | HttpResponse,
    ) -> HttpResponseBase:
        """
        Returns the actual ``HttpResponse`` object after optional validation.

        If it is already the :class:`django.http.HttpResponse` object,
        just validates it before returning.
        """
        try:
            return self._validate_response(controller, raw_data)
        except (  # noqa: WPS239
            ResponseSchemaError,
            ValidationError,
            DataRenderingError,
            InternalServerError,
        ) as exc:
            # We can't call `self.handle_error` or `self.handle_async_error`
            # in exception handlers here,
            # because it is too late. Since `ResponseSchemaError`
            # happened most likely because the return
            # schema validation was not successful.
            return controller.to_error(
                controller.format_error(exc),
                status_code=exc.status_code,
            )

    def _validate_response(
        self,
        controller: 'Controller[BaseSerializer]',
        response_data: Any | HttpResponseBase,
    ) -> HttpResponseBase:
        if isinstance(response_data, HttpResponseBase):
            return self.response_validator.validate_response(
                self,
                controller,
                response_data,
            )

        validated = self.response_validator.validate_modification(
            self,
            controller,
            response_data,
        )
        return self._build_new_response(controller, validated)

    def _build_new_response(
        self,
        controller: 'Controller[BaseSerializer]',
        validated: 'ValidatedModification',
    ) -> HttpResponseBase:
        return controller.to_response(
            validated.raw_data,
            status_code=validated.status_code,
            headers=validated.headers,
            cookies=validated.cookies,
            renderer=validated.renderer,
        )

    def _global_error_handler(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Import the global error handling and call it.

        If not class level error handling has happened.
        """
        return resolve_setting(  # type: ignore[no-any-return]
            Settings.global_error_handler,
            import_string=True,
        )(self, controller, exc)


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar(
    '_ResponseT',
    bound=HttpResponseBase | Awaitable[HttpResponseBase],
)


@overload
def validate(  # noqa: WPS234
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    error_handler: AsyncErrorHandler,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
) -> Callable[
    [Callable[_ParamT, Awaitable[HttpResponseBase]]],
    Callable[_ParamT, Awaitable[HttpResponseBase]],
]: ...


@overload
def validate(
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    error_handler: SyncErrorHandler,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
) -> Callable[
    [Callable[_ParamT, HttpResponseBase]],
    Callable[_ParamT, HttpResponseBase],
]: ...


@overload
def validate(
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    error_handler: None = None,
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
) -> Callable[
    [Callable[_ParamT, _ResponseT]],
    Callable[_ParamT, _ResponseT],
]: ...


def validate(  # noqa: WPS211  # pyright: ignore[reportInconsistentOverload]
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    error_handler: SyncErrorHandler | AsyncErrorHandler | None = None,
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
) -> (
    Callable[
        [Callable[_ParamT, Awaitable[HttpResponseBase]]],
        Callable[_ParamT, Awaitable[HttpResponseBase]],
    ]
    | Callable[
        [Callable[_ParamT, HttpResponseBase]],
        Callable[_ParamT, HttpResponseBase],
    ]
):
    """
    Decorator to validate responses from endpoints that return ``HttpResponse``.

    Apply it to validate important API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django.http import HttpResponse
        >>> from dmr import Controller, validate, ResponseSpec
        >>> from dmr.plugins.pydantic import PydanticSerializer

        >>> class TaskController(Controller[PydanticSerializer]):
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

    Returns:
        The same function with ``__dmr_payload__`` payload instance.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_payload(
        payload=ValidateEndpointPayload(
            responses=[response, *responses],
            validate_responses=validate_responses,
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
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            deprecated=deprecated,
            external_docs=external_docs,
            callbacks=callbacks,
            servers=servers,
        ),
    )


@overload
def modify(
    *,
    # TODO: make error handlers generic?
    error_handler: AsyncErrorHandler,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
    cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    response_description: str | None = None,
) -> ModifyAsyncCallable: ...


@overload
def modify(
    *,
    error_handler: SyncErrorHandler,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
    cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    links: dict[str, Link | Reference] | None = None,
    response_description: str | None = None,
) -> ModifySyncCallable: ...


@overload
def modify(
    *,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
    cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
    validate_responses: bool | None = None,
    semantic_responses: bool | None = None,
    exclude_semantic_responses: Set[HTTPStatus] | None = frozenset(),
    validate_events: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = frozenset(),
    error_handler: None = None,
    parsers: Sequence[Parser] | None = None,
    renderers: Sequence[Renderer] | None = None,
    validate_negotiation: bool | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    links: dict[str, Link | Reference] | None = None,
    response_description: str | None = None,
) -> ModifyAnyCallable: ...


def modify(  # noqa: WPS211
    *,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader | HeaderSpec] | None = None,
    cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
    validate_responses: bool | None = None,
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
    throttling: Sequence[AsyncThrottle] | Sequence[SyncThrottle] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    links: dict[str, Link | Reference] | None = None,
    response_description: str | None = None,
) -> ModifyAsyncCallable | ModifySyncCallable | ModifyAnyCallable:
    """
    Decorator to modify endpoints that return raw model data.

    Apply it to change some API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from dmr import Controller, modify
        >>> from dmr.plugins.pydantic import PydanticSerializer

        >>> class TaskController(Controller[PydanticSerializer]):
        ...     @modify(status_code=HTTPStatus.ACCEPTED)
        ...     def post(self) -> list[int]:
        ...         return [1, 2]  # id of tasks you have started

    Args:
        status_code: Shows *status_code* in the documentation.
            When *status_code* is passed, always use it by default.
            When not provided, we use smart inference
            based on the HTTP method name for default returned response.
        headers: Shows *headers* in the documentation.
            When *headers* are passed we will add them for the default response.
        cookies: Shows *cookies* in the documentation.
            When *cookies* are passed we will add them for the default response.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        semantic_responses: Should semantic responses be collected
            from different providers for this endpoint.
        exclude_semantic_responses: Set of semantic responses status codes
            that user wants to disable.
        validate_events: Should this endpoint validate events?
            If not set, defaults to the ``validate_responses`` value.
            This value only matters if the response
            will be a streaming response that supports event validation.
        extra_responses: List of extra responses that this endpoint can return.
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
        links: Possible links to other OpenAPI operations.
        response_description: Description for the generated response object.

    Returns:
        The same function with ``__dmr_payload__`` payload instance.

    .. warning::

        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_payload(  # type: ignore[return-value]
        payload=ModifyEndpointPayload(
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            responses=extra_responses,
            validate_responses=validate_responses,
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
        ),
    )


def _add_payload(
    *,
    payload: ModifyEndpointPayload | ValidateEndpointPayload,
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # Add payload for future use in the Endpoint creation.
    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        func.__dmr_payload__ = payload  # type: ignore[attr-defined]
        return func

    return decorator
