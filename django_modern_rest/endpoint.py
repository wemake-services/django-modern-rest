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

from django_modern_rest.headers import (
    NewHeader,
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
        return self._handle_default_error(exc)

    async def handle_async_error(self, exc: Exception) -> HttpResponse:
        """
        Return error response if possible.

        Override this method to add custom async error handling.
        """
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
        except Exception as exc:
            return self.handle_error(exc)

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


def validate(
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    validate_responses: bool | Empty = EmptyObj,
) -> Callable[[Callable[_ParamT, _ResponseT]], Callable[_ParamT, _ResponseT]]:
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

    Returns:
        The same function with ``__payload__``
        metadata instance of :class:`EndpointMetadata`.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_payload(
        payload=ValidateEndpointPayload(
            responses=[response, *responses],
            validate_responses=validate_responses,
        ),
    )


class _ModifyCallable(Protocol):
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


def modify(
    *,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    validate_responses: bool | Empty = EmptyObj,
    extra_responses: list[ResponseDescription] | Empty = EmptyObj,
) -> _ModifyCallable:
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

    Returns:
        The same function with ``__payload__``
        metadata instance of :class:`EndpointMetadata`.

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
        validate_method_name(func.__name__)
        func.__payload__ = payload  # type: ignore[attr-defined]
        return func

    return decorator
