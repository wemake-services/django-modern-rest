import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Never,
    overload,
)

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from typing_extensions import ParamSpec, Protocol, TypeVar, deprecated

from django_modern_rest.cookies import NewCookie
from django_modern_rest.errors import AsyncErrorHandler, SyncErrorHandler
from django_modern_rest.exceptions import (
    InternalServerError,
    NotAuthenticatedError,
    ResponseSchemaError,
    ValidationError,
)
from django_modern_rest.headers import NewHeader
from django_modern_rest.metadata import EndpointMetadata, ResponseSpec
from django_modern_rest.negotiation import RequestNegotiator, ResponseNegotiator
from django_modern_rest.openapi.objects import (
    Callback,
    ExternalDocumentation,
    Reference,
    Server,
)
from django_modern_rest.parsers import Parser
from django_modern_rest.renderers import Renderer
from django_modern_rest.response import APIError
from django_modern_rest.security.base import AsyncAuth, SyncAuth
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.settings import (
    HttpSpec,
    Settings,
    resolve_setting,
)
from django_modern_rest.validation import (
    EndpointMetadataBuilder,
    EndpointMetadataValidator,
    ModifyEndpointPayload,
    Payload,
    ResponseValidator,
    ValidateEndpointPayload,
    validate_method_name,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller


# TODO: make generic
class Endpoint:  # noqa: WPS214
    """
    Represents the single API endpoint.

    Is built during the import time.
    In the runtime only does response validate, which can be disabled.
    """

    __slots__ = (
        '_func',
        '_method',
        'is_async',
        'metadata',
        'request_negotiator',
        'response_negotiator',
        'response_validator',
    )

    _func: Callable[..., Any]

    metadata_builder_cls: ClassVar[type[EndpointMetadataBuilder]] = (
        EndpointMetadataBuilder
    )
    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        EndpointMetadataValidator
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """
        Create an entrypoint.

        Args:
            func: Entrypoint handler. An actual function to be called.
            controller_cls: ``Controller`` class that this endpoint belongs to.
            blueprint_cls: ``Blueprint`` class that this endpoint
                might belong to.

        .. danger::

            Endpoint object must not have any mutable instance state,
            because its instance is reused for all requests.

        """
        # We need to add payloads to functions that don't have it,
        # since decorator is optional:
        payload: Payload = getattr(func, '__payload__', None)
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
        )(
            func,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
        )
        self.metadata_validator_cls(metadata=metadata)(
            func,
            payload=payload,
            blueprint_cls=blueprint_cls,
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
        )

        # We need a func before any wrappers, but with metadata:
        self.response_validator = self.response_validator_cls(
            metadata,
            controller_cls.serializer,
        )
        # We can now run endpoint's optimization:
        controller_cls.serializer.optimizer.optimize_endpoint(metadata)

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
    ) -> HttpResponse:
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
    ) -> HttpResponse:
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
        if controller.blueprint:
            try:
                return controller.blueprint.handle_error(
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                pass  # noqa: WPS420
        # Per-endpoint error handler and per-blueprint handlers didn't work.
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
        if controller.blueprint:
            try:
                return await controller.blueprint.handle_async_error(
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                pass  # noqa: WPS420
        # Per-endpoint error handler and per-blueprint handlers didn't work.
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

    def _async_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Awaitable[HttpResponse]]:
        # NOTE: if you change something here, also change in `_sync_endpoint`
        async def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            active_blueprint = controller.active_blueprint
            try:  # noqa: WPS229
                # Negotiate response:
                self.response_negotiator(controller.request)

                # Run checks:
                await self._run_async_checks(controller)

                # Parse request:
                active_blueprint._serializer_context.parse_and_bind(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    self,
                    active_blueprint,
                )

                # Return response:
                func_result = await func(active_blueprint)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = active_blueprint.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            except Exception as exc:
                func_result = await self.handle_async_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., HttpResponse]:
        # NOTE: if you change something here, also change in `_async_endpoint`
        def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            active_blueprint = controller.active_blueprint

            try:  # noqa: WPS229
                # Negotiate response:
                self.response_negotiator(controller.request)

                # Run checks:
                self._run_checks(controller)

                # Parse request:
                active_blueprint._serializer_context.parse_and_bind(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    self,
                    active_blueprint,
                )

                # Return response:
                func_result = func(active_blueprint)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = active_blueprint.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            except Exception as exc:
                func_result = self.handle_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    def _run_checks(self, controller: 'Controller[BaseSerializer]') -> None:
        # Run auth checks:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, SyncAuth)  # noqa: S101
            try:
                user = auth(self, controller)
            except PermissionDenied:
                raise NotAuthenticatedError from None
            else:
                if user is not None:
                    return
        raise NotAuthenticatedError

    async def _run_async_checks(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        # Run auth checks:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, AsyncAuth)  # noqa: S101
            try:
                user = await auth(self, controller)  # noqa: WPS476
            except PermissionDenied:
                raise NotAuthenticatedError from None
            else:
                if user is not None:
                    return
        raise NotAuthenticatedError

    def _make_http_response(
        self,
        controller: 'Controller[BaseSerializer]',
        raw_data: Any | HttpResponse,
    ) -> HttpResponse:
        """
        Returns the actual ``HttpResponse`` object after optional validation.

        If it is already the :class:`django.http.HttpResponse` object,
        just validates it before returning.
        """
        try:
            return self._validate_response(controller, raw_data)
        except (
            ResponseSchemaError,
            ValidationError,
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
        raw_data: Any | HttpResponse,
    ) -> HttpResponse:
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(
                self,
                controller,
                raw_data,
            )

        validated = self.response_validator.validate_modification(
            self,
            controller,
            raw_data,
        )
        return controller.to_response(
            validated.raw_data,
            status_code=validated.status_code,
            headers=validated.headers,
            cookies=validated.cookies,
            renderer_cls=validated.renderer_cls,
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
_ResponseT = TypeVar('_ResponseT', bound=HttpResponse | Awaitable[HttpResponse])


@overload
def validate(  # noqa: WPS234
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    error_handler: AsyncErrorHandler,
    validate_responses: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
) -> Callable[
    [Callable[_ParamT, Awaitable[HttpResponse]]],
    Callable[_ParamT, Awaitable[HttpResponse]],
]: ...


@overload
def validate(
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    error_handler: SyncErrorHandler,
    validate_responses: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> Callable[
    [Callable[_ParamT, HttpResponse]],
    Callable[_ParamT, HttpResponse],
]: ...


@overload
def validate(
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    validate_responses: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    error_handler: None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> Callable[
    [Callable[_ParamT, _ResponseT]],
    Callable[_ParamT, _ResponseT],
]: ...


def validate(  # noqa: WPS211  # pyright: ignore[reportInconsistentOverload]
    response: ResponseSpec,
    /,
    *responses: ResponseSpec,
    validate_responses: bool | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    error_handler: SyncErrorHandler | AsyncErrorHandler | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> (
    Callable[
        [Callable[_ParamT, Awaitable[HttpResponse]]],
        Callable[_ParamT, Awaitable[HttpResponse]],
    ]
    | Callable[
        [Callable[_ParamT, HttpResponse]],
        Callable[_ParamT, HttpResponse],
    ]
):
    """
    Decorator to validate responses from endpoints that return ``HttpResponse``.

    Apply it to validate important API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django.http import HttpResponse
        >>> from django_modern_rest import (
        ...     Controller,
        ...     validate,
        ...     ResponseSpec,
        ... )
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

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
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this endpoint.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        allow_custom_http_methods: Should we allow custom HTTP
            methods for this endpoint. By "custom" we mean ones that
            are not in :class:`http.HTTPMethod` enum.
        parsers: Sequence of types to be used for this endpoint
            to parse incoming request's body. All types must be subtypes
            of :class:`~django_modern_rest.parsers.Parser`.
        renderers: Sequence of types to be used for this endpoint
            to render response's body. All types must be subtypes
            of :class:`~django_modern_rest.renderers.Renderer`.
        auth: Sequence of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`django_modern_rest.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`django_modern_rest.security.AsyncAuth`.
            Set it to ``None`` to disable auth for this endpoint.
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
            If a servers array is specified at the Path Item Object or
            OpenAPI Object level, it will be overridden by this value.
        metadata_cls: Subclass of
            :class:`django_modern_rest.metadata.EndpointMetadata` that will
            be used to populate endpoint's metadata.

    Returns:
        The same function with ``__payload__`` payload instance.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_payload(
        payload=ValidateEndpointPayload(
            responses=[response, *responses],
            validate_responses=validate_responses,
            no_validate_http_spec=no_validate_http_spec,
            error_handler=error_handler,
            allow_custom_http_methods=allow_custom_http_methods,
            parsers=parsers,
            renderers=renderers,
            auth=auth,
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            deprecated=deprecated,
            external_docs=external_docs,
            callbacks=callbacks,
            servers=servers,
            metadata_cls=metadata_cls,
        ),
    )


class _ModifyAsyncCallable(Protocol):
    """Make `@modify` on functions returning `HttpResponse` unrepresentable."""

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _ResponseT], /) -> Never: ...

    @overload
    def __call__(
        self,
        func: Callable[_ParamT, Awaitable[_ReturnT]],
        /,
    ) -> Callable[_ParamT, _ReturnT]: ...


class _ModifySyncCallable(Protocol):
    """Make `@modify` on functions returning `HttpResponse` unrepresentable."""

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _ResponseT], /) -> Never: ...

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Passing sync `error_hanlder` to `@modify` requires sync endpoint',
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


class _ModifyAnyCallable(Protocol):
    """Make `@modify` on functions returning `HttpResponse` unrepresentable."""

    @overload
    @deprecated(
        # It is not actually deprecated, but impossible for the day one.
        # But, this is the only way to trigger a typing error.
        'Do not use `@modify` decorator with `HttpResponse` return type',
    )
    def __call__(self, func: Callable[_ParamT, _ResponseT], /) -> Never: ...

    @overload
    def __call__(
        self,
        func: Callable[_ParamT, _ReturnT],
        /,
    ) -> Callable[_ParamT, _ReturnT]: ...


@overload
def modify(
    *,
    # TODO: make error handlers generic?
    error_handler: AsyncErrorHandler,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    validate_responses: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> _ModifyAsyncCallable: ...


@overload
def modify(
    *,
    error_handler: SyncErrorHandler,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    validate_responses: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> _ModifySyncCallable: ...


@overload
def modify(
    *,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    validate_responses: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    error_handler: None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> _ModifyAnyCallable: ...


def modify(  # noqa: WPS211
    *,
    status_code: HTTPStatus | None = None,
    headers: Mapping[str, NewHeader] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    validate_responses: bool | None = None,
    extra_responses: list[ResponseSpec] | None = None,
    no_validate_http_spec: Set[HttpSpec] | None = None,
    error_handler: SyncErrorHandler | AsyncErrorHandler | None = None,
    allow_custom_http_methods: bool = False,
    parsers: Sequence[type[Parser]] | None = None,
    renderers: Sequence[type[Renderer]] | None = None,
    auth: Sequence[AsyncAuth] | Sequence[SyncAuth] | None = (),
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    external_docs: ExternalDocumentation | None = None,
    callbacks: dict[str, Callback | Reference] | None = None,
    servers: list[Server] | None = None,
    metadata_cls: type[EndpointMetadata] = EndpointMetadata,
) -> _ModifyAsyncCallable | _ModifySyncCallable | _ModifyAnyCallable:
    """
    Decorator to modify endpoints that return raw model data.

    Apply it to change some API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django_modern_rest import Controller, modify
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

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
        extra_responses: List of extra responses that this endpoint can return.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this endpoint.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        allow_custom_http_methods: Should we allow custom HTTP
            methods for this endpoint. By "custom" we mean ones that
            are not in :class:`http.HTTPMethod` enum.
        parsers: Sequence of types to be used for this endpoint
            to parse incoming request's body. All types must be subtypes
            of :class:`~django_modern_rest.parsers.Parser`.
        renderers: Sequence of types to be used for this endpoint
            to render response's body. All types must be subtypes
            of :class:`~django_modern_rest.renderers.Renderer`.
        auth: Sequence of auth instances to be used for this endpoint.
            Sync endpoints must use instances
            of :class:`django_modern_rest.security.SyncAuth`.
            Async endpoints must use instances
            of :class:`django_modern_rest.security.AsyncAuth`.
            Set it to ``None`` to disable auth for this endpoint.
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
            If a servers array is specified at the Path Item Object or
            OpenAPI Object level, it will be overridden by this value.
        metadata_cls: Subclass of
            :class:`django_modern_rest.metadata.EndpointMetadata` that will
            be used to populate endpoint's metadata.

    Returns:
        The same function with ``__payload__`` payload instance.

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
            no_validate_http_spec=no_validate_http_spec,
            error_handler=error_handler,
            allow_custom_http_methods=allow_custom_http_methods,
            parsers=parsers,
            renderers=renderers,
            auth=auth,
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            deprecated=deprecated,
            external_docs=external_docs,
            callbacks=callbacks,
            servers=servers,
            metadata_cls=metadata_cls,
        ),
    )


def _add_payload(
    *,
    payload: ModifyEndpointPayload | ValidateEndpointPayload,
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # Add payload for future use in the Endpoint validation.
    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        validate_method_name(
            func.__name__,
            allow_custom_http_methods=payload.allow_custom_http_methods,
        )
        func.__payload__ = payload  # type: ignore[attr-defined]
        return func

    return decorator
