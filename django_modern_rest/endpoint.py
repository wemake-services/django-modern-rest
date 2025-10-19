import inspect
from collections.abc import Awaitable, Callable, Mapping
from http import HTTPMethod, HTTPStatus
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
from django_modern_rest.types import (
    Empty,
    EmptyObj,
)
from django_modern_rest.validation import (
    EndpointMetadataValidator,
    ModifyEndpointPayload,
    ResponseValidator,
    ValidateEndpointPayload,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:
    """
    Represents the single API endpoint.

    Is built during the import time.
    In the runtime only does response validate, which can be disabled.
    """

    __slots__ = (
        '_func',
        'endpoint_optimizer',
        'is_async',
        'method',
        'response_validator',
    )

    _func: Callable[..., Any]

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
        serializer: type[BaseSerializer],
    ) -> None:
        """
        Create an entrypoint.

        Args:
            func: Entrypoint handler. An actual function.
            serializer: ``BaseSerializer`` type that can parse and validate.

        """
        self.method = HTTPMethod(func.__name__.upper())
        # We need to add metadata to functions that don't have it,
        # since decorator is optional:
        func = (
            _add_metadata(
                metadata_validator_cls=self.metadata_validator_cls,
                payload=None,
            )(func)
            if getattr(func, '__endpoint__', None) is None
            else func
        )
        metadata = func.__endpoint__  # type: ignore[attr-defined]
        # We need a func before any wrappers, but with metadata:
        self.response_validator = self.response_validator_cls(
            metadata,
            serializer,
        )
        # We can now run endpoint's optimization:
        serializer.optimizer.optimize_endpoint(metadata)

        # Now we can add wrappers:
        if inspect.iscoroutinefunction(func):
            self._func = self._async_endpoint(func)
            self.is_async = True
        else:
            self._func = self._sync_endpoint(func)
            self.is_async = False

    def __call__(
        self,
        controller: 'Controller[Any]',
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Run the endpoint and return the response."""
        return self._func(controller, *args, **kwargs)  # type: ignore[no-any-return]

    def _async_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Awaitable[HttpResponse]]:
        async def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            try:
                func_result = await func(controller, *args, **kwargs)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = controller.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            return self._make_http_response(controller, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., HttpResponse]:
        def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            try:
                func_result = func(controller, *args, **kwargs)
            except APIError as exc:  # pyright: ignore[reportUnknownVariableType]
                func_result = controller.to_error(
                    exc.raw_data,  # pyright: ignore[reportUnknownMemberType]
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
            return self._make_http_response(controller, func_result)

        return decorator

    def _make_http_response(
        self,
        controller: 'Controller[BaseSerializer]',
        raw_data: Any,
    ) -> HttpResponse:
        """Returns the actual `HttpResponse` object."""
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(
                controller,
                raw_data,
            )

        validated = self.response_validator.validate_modification(
            controller,
            raw_data,
        )
        return HttpResponse(
            content=controller.serializer.to_json(validated.raw_data),
            status=validated.status_code,
            headers=validated.headers,
        )


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar('_ResponseT', bound=HttpResponse | Awaitable[HttpResponse])


def validate(
    response: ResponseDescription,
    /,
    *responses: ResponseDescription,
    metadata_validator_cls: type[
        EndpointMetadataValidator
    ] = EndpointMetadataValidator,
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
        metadata_validator_cls: Type that will validate
            the endpoint definition by default. Can be customized.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.

    Raises:
        EndpointMetadataError: When metadata is not valid.

    Returns:
        The same function with ``__endpoint__``
        metadata instance of :class:`EndpointMetadata`.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_metadata(
        payload=ValidateEndpointPayload(
            responses=[response, *responses],
            validate_responses=validate_responses,
        ),
        metadata_validator_cls=metadata_validator_cls,
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
    metadata_validator_cls: type[
        EndpointMetadataValidator
    ] = EndpointMetadataValidator,
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
        metadata_validator_cls: Type that will validate
            the endpoint definition by default. Can be customized.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.

    Returns:
        The same function with ``__endpoint__``
        metadata instance of :class:`EndpointMetadata`.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is performance critical for you!

    """
    return _add_metadata(  # type: ignore[return-value]
        payload=ModifyEndpointPayload(
            status_code=status_code,
            headers=headers,
            responses=extra_responses,
            validate_responses=validate_responses,
        ),
        metadata_validator_cls=metadata_validator_cls,
    )


def _add_metadata(
    *,
    metadata_validator_cls: type[EndpointMetadataValidator],
    payload: ModifyEndpointPayload | ValidateEndpointPayload | None,
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # It is cheap for us to do the endpoint metadata calculation here,
    # because we do it once per module import.
    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        metadata = metadata_validator_cls(payload=payload)(func)

        # Validation passed, now we can create valid metadata:
        func.__endpoint__ = metadata  # type: ignore[attr-defined]
        return func

    return decorator
