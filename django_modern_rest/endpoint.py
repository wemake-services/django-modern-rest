import inspect
from collections.abc import Awaitable, Callable, Mapping
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Never,
    overload,
)

from django.http import HttpResponse
from typing_extensions import ParamSpec, Protocol, TypeVar, deprecated

from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.headers import (
    NewHeader,
)
from django_modern_rest.openapi.objects import (
    ExternalDocumentation,
    SecurityRequirement,
)
from django_modern_rest.response import APIError, ResponseDescription
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_GLOBAL_ERROR_HANDLER_KEY,
    resolve_setting,
)
from django_modern_rest.types import (
    Empty,
    EmptyObj,
)
from django_modern_rest.validation import (
    EndpointMetadataValidator,
    ModifyEndpointPayload,
    PayloadT,
    ResponseValidator,
    ValidateEndpointPayload,
    validate_method_name,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:  # noqa: WPS214
    """
    Represents the single API endpoint.

    Is built during the import time.
    In the runtime only does response validate, which can be disabled.
    """

    __slots__ = (
        '_controller',
        '_func',
        '_method',
        'is_async',
        'metadata',
        'response_validator',
    )

    _func: Callable[..., Any]
    _controller: 'Controller[BaseSerializer]'

    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        EndpointMetadataValidator
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
            func: Entrypoint handler. An actual function.
            controller_cls: ``Controller`` class that this endpoint belongs to.

        """
        payload: PayloadT = getattr(func, '__payload__', None)
        # We need to add metadata to functions that don't have it,
        # since decorator is optional:
        metadata = self.metadata_validator_cls(payload=payload)(
            func,
            controller_cls=controller_cls,
        )
        func.__metadata__ = metadata  # type: ignore[attr-defined]
        self.metadata = metadata

        # We need a func before any wrappers, but with metadata:
        self.response_validator = self.response_validator_cls(
            metadata,
            controller_cls.serializer,
        )
        # We can now run endpoint's optimization:
        controller_cls.serializer.optimizer.optimize_endpoint(metadata)

        # Now we can add wrappers:
        if inspect.iscoroutinefunction(func):
            self._func = self._async_endpoint(func)
            self.is_async = True
        else:
            self._func = self._sync_endpoint(func)
            self.is_async = False

    def __call__(
        self,
        controller: 'Controller[BaseSerializer]',
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Run the endpoint and return the response."""
        self._controller = controller
        return self._func(*args, **kwargs)  # type: ignore[no-any-return]

    def handle_error(self, exc: Exception) -> HttpResponse:
        """
        Return error response if possible.

        Override this method to add custom error handling.
        """
        if not isinstance(self.metadata.error_handler, Empty):
            try:
                # We validate this, no error possible in runtime:
                return self.metadata.error_handler(  # type: ignore[return-value]
                    self._controller,
                    self,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return self._controller.handle_error(self, exc)
        except Exception:
            # And the last option is to handle error globally:
            return self._handle_default_error(exc)

    async def handle_async_error(self, exc: Exception) -> HttpResponse:
        """
        Return error response if possible.

        Override this method to add custom async error handling.
        """
        if not isinstance(self.metadata.error_handler, Empty):
            try:
                # We validate this, no error possible in runtime:
                return await self.metadata.error_handler(  # type: ignore[no-any-return, misc]
                    self._controller,
                    self,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return await self._controller.handle_async_error(self, exc)
        except Exception:
            # And the last option is to handle error globally:
            return self._handle_default_error(exc)

    def _async_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Awaitable[HttpResponse]]:
        async def decorator(
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            # Parse request:
            try:
                self._controller.serializer_context.parse_and_bind(
                    self._controller,
                    self._controller.request,
                    *args,
                    **kwargs,
                )
            except Exception as exc:
                return self._make_http_response(
                    await self.handle_async_error(exc),
                )
            # Return response:
            try:
                func_result = await func(self._controller)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = self._controller.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            except Exception as exc:
                func_result = await self.handle_async_error(exc)
            return self._make_http_response(func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., HttpResponse]:
        def decorator(
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            # Parse request:
            try:
                self._controller.serializer_context.parse_and_bind(
                    self._controller,
                    self._controller.request,
                    *args,
                    **kwargs,
                )
            except Exception as exc:
                return self._make_http_response(
                    self.handle_error(exc),
                )
            # Return response:
            try:
                func_result = func(self._controller)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = self._controller.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            except Exception as exc:
                func_result = self.handle_error(exc)
            return self._make_http_response(func_result)

        return decorator

    def _make_http_response(self, raw_data: Any | HttpResponse) -> HttpResponse:
        """
        Returns the actual ``HttpResponse`` object after optional validation.

        If it is already the :class:`django.http.HttpResponse` object,
        just validates it before returning.
        """
        try:
            return self._validate_response(raw_data)
        except ResponseSerializationError as exc:
            # We can't call `self.handle_error` or `self.handle_async_error`
            # here, because it is too late. Since `ResponseSerializationError`
            # happened mostly because the return
            # schema validation was not successful.
            payload = {'detail': exc.args[0]}
            return self._controller.to_error(
                payload,
                status_code=exc.status_code,
            )

    def _validate_response(self, raw_data: Any | HttpResponse) -> HttpResponse:
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(
                self._controller,
                raw_data,
            )

        validated = self.response_validator.validate_modification(
            self._controller,
            raw_data,
        )
        return HttpResponse(
            content=self._controller.serializer.serialize(validated.raw_data),
            status=validated.status_code,
            headers=validated.headers,
        )

    def _handle_default_error(self, exc: Exception) -> HttpResponse:
        """
        Import the global error handling and call it.

        If not class level error handling has happened.
        """
        return resolve_setting(  # type: ignore[no-any-return]
            DMR_GLOBAL_ERROR_HANDLER_KEY,
            import_string=True,
        )(self._controller, self, exc)


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar('_ResponseT', bound=HttpResponse | Awaitable[HttpResponse])


@overload
def validate(  # noqa: WPS234
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    error_handler: AsyncErrorHandlerT,
    validate_responses: bool | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> Callable[
    [Callable[_ParamT, Awaitable[HttpResponse]]],
    Callable[_ParamT, Awaitable[HttpResponse]],
]: ...


@overload
def validate(
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    error_handler: SyncErrorHandlerT,
    validate_responses: bool | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> Callable[
    [Callable[_ParamT, HttpResponse]],
    Callable[_ParamT, HttpResponse],
]: ...


@overload
def validate(
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    validate_responses: bool | Empty = EmptyObj,
    error_handler: Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> Callable[
    [Callable[_ParamT, _ResponseT]],
    Callable[_ParamT, _ResponseT],
]: ...


def validate(  # noqa: WPS211  # pyright: ignore[reportInconsistentOverload]
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    validate_responses: bool | Empty = EmptyObj,
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    security: list[SecurityRequirement] | None = None,
    external_docs: ExternalDocumentation | None = None,
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
        ...     ResponseDescription,
        ... )
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class TaskController(Controller[PydanticSerializer]):
        ...     @validate(
        ...         ResponseDescription(
        ...             return_type=list[int],
        ...             status_code=HTTPStatus.OK,
        ...         ),
        ...     )
        ...     def post(self) -> HttpResponse:
        ...         return HttpResponse(b'[1, 2]', status=HTTPStatus.OK)

    Response validation can be disabled for extra speed
    by sending *validate_responses* falsy parameter
    or by setting this configuration in your ``settings.py`` file:

    .. code:: python

        >>> DMR_SETTINGS = {'validate_responses': False}

    Args:
        response: The main response that this endpoint is allowed to return.
        responses: A collection of other responses that are allowed
            to be returned from this endpoint.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        allow_custom_http_methods: Should we allow custom HTTP
            methods for this endpoint. By "custom" we mean ones that
            are not in :class:`http.HTTPMethod` enum.
        summary: A short summary of what the operation does.
            Used in OpenAPI documentation.
        description: A verbose explanation of the operation behavior.
            Used in OpenAPI documentation.
        tags: A list of tags for API documentation control.
            Used to group operations in OpenAPI documentation.
        operation_id: Unique string used to identify the operation.
            Used in OpenAPI documentation.
        deprecated: Declares this operation to be deprecated.
            Used in OpenAPI documentation.
        security: A declaration of which security mechanisms can be used
            for this operation. Used in OpenAPI documentation.
        external_docs: Additional external documentation for this operation.
            Used in OpenAPI documentation.

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
            error_handler=error_handler,
            allow_custom_http_methods=allow_custom_http_methods,
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            deprecated=deprecated,
            security=security,
            external_docs=external_docs,
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
    error_handler: AsyncErrorHandlerT,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    validate_responses: bool | Empty = EmptyObj,
    extra_responses: list[ResponseDescription] | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> _ModifyAsyncCallable: ...


@overload
def modify(
    *,
    error_handler: SyncErrorHandlerT,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    validate_responses: bool | Empty = EmptyObj,
    extra_responses: list[ResponseDescription] | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> _ModifySyncCallable: ...


@overload
def modify(
    *,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    validate_responses: bool | Empty = EmptyObj,
    extra_responses: list[ResponseDescription] | Empty = EmptyObj,
    error_handler: Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
) -> _ModifyAnyCallable: ...


def modify(  # noqa: WPS211
    *,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    validate_responses: bool | Empty = EmptyObj,
    extra_responses: list[ResponseDescription] | Empty = EmptyObj,
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | Empty = EmptyObj,
    allow_custom_http_methods: bool = False,
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    operation_id: str | None = None,
    deprecated: bool = False,
    security: list[SecurityRequirement] | None = None,
    external_docs: ExternalDocumentation | None = None,
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
            Use non-empty ``value`` parameter
            of :data:`django_modern_rest.headers.ResponseHeadersT` object.
        extra_responses: List of extra responses that this endpoint can return.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        error_handler: Callback function to be called
            when this endpoint faces an exception.
        allow_custom_http_methods: Should we allow custom HTTP
            methods for this endpoint. By "custom" we mean ones that
            are not in :class:`http.HTTPMethod` enum.
        summary: A short summary of what the operation does.
            Used in OpenAPI documentation.
        description: A verbose explanation of the operation behavior.
            Used in OpenAPI documentation.
        tags: A list of tags for API documentation control.
            Used to group operations in OpenAPI documentation.
        operation_id: Unique string used to identify the operation.
            Used in OpenAPI documentation.
        deprecated: Declares this operation to be deprecated.
            Used in OpenAPI documentation.
        security: A declaration of which security mechanisms can be used
            for this operation. Used in OpenAPI documentation.
        external_docs: Additional external documentation for this operation.
            Used in OpenAPI documentation.

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
            responses=extra_responses,
            validate_responses=validate_responses,
            error_handler=error_handler,
            allow_custom_http_methods=allow_custom_http_methods,
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            deprecated=deprecated,
            security=security,
            external_docs=external_docs,
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
