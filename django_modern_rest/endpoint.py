import dataclasses
import inspect
from collections.abc import Awaitable, Callable, Mapping
from http import HTTPMethod, HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Never,
    TypeAlias,
    final,
    overload,
)

from django.http import HttpResponse
from typing_extensions import ParamSpec, Protocol, TypeVar, deprecated

from django_modern_rest.headers import (
    HeaderDescription,
    NewHeader,
    ResponseHeadersT,
)
from django_modern_rest.response import infer_status_code
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    parse_return_annotation,
)
from django_modern_rest.validation import (
    EndpointMetadataValidator,
    ResponseValidator,
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
            self._func = self._async_endpoint(func, serializer)
            self.is_async = True
        else:
            self._func = self._sync_endpoint(func, serializer)
            self.is_async = False

    def __call__(
        self,
        contoller: 'Controller[Any]',
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Run the endpoint and return the response."""
        return self._func(contoller, *args, **kwargs)  # type: ignore[no-any-return]

    def _async_endpoint(
        self,
        func: Callable[..., Any],
        serializer: type[BaseSerializer],
    ) -> Callable[..., Awaitable[HttpResponse]]:
        async def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            func_result = await func(controller, *args, **kwargs)
            return self._make_http_response(controller, serializer, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
        serializer: type[BaseSerializer],
    ) -> Callable[..., HttpResponse]:
        def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            func_result = func(controller, *args, **kwargs)
            return self._make_http_response(controller, serializer, func_result)

        return decorator

    def _make_http_response(
        self,
        controller: 'Controller[BaseSerializer]',
        serializer: type[BaseSerializer],
        raw_data: Any,
    ) -> HttpResponse:
        """Returns the actual `HttpResponse` object."""
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(
                controller,
                raw_data,
            )

        validated = self.response_validator.validate_content(
            controller,
            raw_data,
        )
        return HttpResponse(
            content=serializer.to_json(validated.raw_data),
            status=validated.status_code,
            headers=validated.headers,
        )


_ExplicitDecoratorNameT: TypeAlias = Literal['modify', 'validate'] | None


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata:
    """
    Endpoint metadata specification.

    Attrs:
        return_type: Stores optional return type that is specified either
            via return type annotation for raw data responses,
            or via ``return_type`` parameter to :func:`validate`.
        status_code: Status code to be returned.
            Can be infered from the HTTP method name.
        headers: Optinal headers that response will return.
        method: HTTP method for this endpoint.
        explicit_decorator_name: Was this metadata created
            with an explicit decorator call?
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.

    """

    # Can be provided only when dealing with `HttpResponse` returns:
    return_type: Any | Empty
    validate_responses: bool | Empty

    # Can be provided at all times:
    status_code: HTTPStatus
    headers: ResponseHeadersT | Empty
    method: HTTPMethod
    explicit_decorator_name: _ExplicitDecoratorNameT

    def build_headers(self, serializer: type[BaseSerializer]) -> dict[str, Any]:
        """Returns headers with values for raw data endpoints."""
        headers: dict[str, Any] = {'Content-Type': serializer.content_type}
        if isinstance(self.headers, Empty):
            return headers
        headers.update({
            header_name: response_header.value
            for header_name, response_header in self.headers.items()
        })
        return headers


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar('_ResponseT', bound=HttpResponse | Awaitable[HttpResponse])


def validate(
    *,
    return_type: Any,
    status_code: HTTPStatus,
    headers: Mapping[str, HeaderDescription] | Empty = EmptyObj,
    metadata_validator_cls: type[
        EndpointMetadataValidator
    ] = EndpointMetadataValidator,
    validate_responses: bool | Empty = EmptyObj,
    # TODO:
    # errors
    # schema_modifications
    # cookies
    # file downloads
) -> Callable[[Callable[_ParamT, _ResponseT]], Callable[_ParamT, _ResponseT]]:
    """
    Decorator to validate responses from endpoints that return ``HttpResponse``.

    Apply it to validate important API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django.http import HttpResponse
        >>> from django_modern_rest import Controller, validate
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class TaskContoller(Controller[PydanticSerializer]):
        ...     @validate(return_type=list[int], status_code=HTTPStatus.OK)
        ...     def post(self) -> HttpResponse:
        ...         return HttpResponse(b'[1, 2]', status=HTTPStatus.OK)

    Response validation can be disabled for extra speed
    by sending *validate_responses* falsy parameter
    or by setting this configuration in your ``settings.py`` file:

    .. code:: python

        >>> DMR_SETTINGS = {'validate_responses': False}

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, can be turned off.
        status_code: Shows *status_code* in the documentation
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response. Headers with ``value`` attribute set
            will be added to the final response.
        metadata_validator_cls: Type that will validate
            the endpoint definition by deafult. Can be customized.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.

    Raises:
        EndpointMetadataError: When user did not specify
            some required metadata entries.

    Returns:
        The same function with ``__endpoint__``
        metadata instanse of :class:`EndpointMetadata`.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is preformance critical for you!

    """
    return _add_metadata(
        return_type=return_type,
        status_code=status_code,
        headers=headers,
        explicit_decorator_name='validate',
        metadata_validator_cls=metadata_validator_cls,
        validate_responses=validate_responses,
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
    # `type[T]` limits some type annotations:
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: Mapping[str, NewHeader] | Empty = EmptyObj,
    metadata_validator_cls: type[
        EndpointMetadataValidator
    ] = EndpointMetadataValidator,
    validate_responses: bool | Empty = EmptyObj,
) -> _ModifyCallable:
    """
    Decorator to modify endpoints that return raw model data.

    Apply it to change some API parts:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django_modern_rest import Controller, modify
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class TaskContoller(Controller[PydanticSerializer]):
        ...     @modify(status_code=HTTPStatus.ACCEPTED)
        ...     def post(self) -> list[int]:
        ...         return [1, 2]  # id of tasks you have started

    Args:
        status_code: Shows *status_code* in the documentation.
            When *status_code* is passed, always uses it for
            all responses. When not provided, we use smart inference
            based on the HTTP method name.
        headers: Shows *headers* in the documentation.
            When *headers* are passed we will add them for all responses.
            Use non-empty ``value`` parameter
            of :class:`django_modern_rest.headers.BaseHeaderDescription` object.
        metadata_validator_cls: Type that will validate
            the endpoint definition by deafult. Can be customized.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.

    Returns:
        The same function with ``__endpoint__``
        metadata instanse of :class:`EndpointMetadata`.

    .. warning::
        Do not disable ``validate_responses`` unless
        this is preformance critical for you!

    """
    return _add_metadata(  # type: ignore[return-value]
        status_code=status_code,
        headers=headers,
        explicit_decorator_name='modify',
        metadata_validator_cls=metadata_validator_cls,
        validate_responses=validate_responses,
    )


def _add_metadata(  # noqa: WPS211
    *,
    return_type: Any | Empty = EmptyObj,
    status_code: HTTPStatus | Empty = EmptyObj,
    headers: ResponseHeadersT | Empty = EmptyObj,
    explicit_decorator_name: _ExplicitDecoratorNameT = None,
    metadata_validator_cls: type[
        EndpointMetadataValidator
    ] = EndpointMetadataValidator,
    validate_responses: bool | Empty = EmptyObj,
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # It is cheap for us to do the endpoint metadata calculation here,
    # because we do it once per module import.
    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        return_annotation = parse_return_annotation(func)
        infered_return_type = (
            return_annotation if isinstance(return_type, Empty) else return_type
        )
        method = HTTPMethod(func.__name__.upper())
        status = (
            infer_status_code(method)
            if isinstance(status_code, Empty)
            else status_code
        )

        metadata_validator_cls(
            func=func,
            explicit_decorator_name=explicit_decorator_name,
            headers=headers,
            status_code=status,
            return_type=infered_return_type,
        )(return_annotation)

        # Validation passed, now we can create valid metadata:
        func.__endpoint__ = EndpointMetadata(  # type: ignore[attr-defined]
            return_type=infered_return_type,
            status_code=status,
            headers=headers,
            explicit_decorator_name=explicit_decorator_name,
            method=method,
            validate_responses=validate_responses,
        )
        return func

    return decorator
