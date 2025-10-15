import dataclasses
import inspect
from collections.abc import Awaitable, Callable
from http import HTTPMethod, HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Never,
    Protocol,
    final,
    overload,
)

from django.http import HttpResponse
from typing_extensions import ParamSpec, TypeVar, deprecated

from django_modern_rest.exceptions import (
    MissingEndpointMetadataError,
    ResponseSerializationError,
)
from django_modern_rest.responses import ResponseValidator
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    is_safe_subclass,
    parse_return_annotation,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:
    __slots__ = ('_func', 'is_async', 'response_validator')

    _func: Callable[..., Any]

    response_validator_cls: ClassVar[type[ResponseValidator]] = (
        ResponseValidator
    )

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        serializer: type[BaseSerializer],
    ) -> None:
        # We need to add metadata to functions that don't have it,
        # since decorator is optional:
        func = (
            _add_metadata()(func)
            if getattr(func, '__endpoint__', None) is None
            else func
        )
        self.response_validator = self.response_validator_cls(
            func,  # we need a func before any wrappers
            serializer=serializer,
        )
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
        return self._func(contoller, *args, **kwargs)  # type: ignore[no-any-return]

    def _async_endpoint(
        self,
        func: Callable[..., Any],
        serializer: type[BaseSerializer],
    ) -> Callable[..., Awaitable[HttpResponse]]:
        async def decorator(*args: Any, **kwargs: Any) -> HttpResponse:
            func_result = await func(*args, **kwargs)
            return self._make_http_response(serializer, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
        serializer: type[BaseSerializer],
    ) -> Callable[..., HttpResponse]:
        def decorator(*args: Any, **kwargs: Any) -> HttpResponse:
            func_result = func(*args, **kwargs)
            return self._make_http_response(serializer, func_result)

        return decorator

    # TODO: support headers, metadata, etc
    def _make_http_response(
        self,
        serializer: type[BaseSerializer],
        raw_data: Any,
    ) -> HttpResponse:
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(raw_data)

        validated = self.response_validator.validate_content(raw_data)
        return HttpResponse(
            content=serializer.to_json(validated.raw_data),
            content_type='application/json',  # TODO: also validated
            status=validated.status_code,
        )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata:
    """
    Endpoint metadata specification.

    Stored inside ``__endpoint__`` attribute of functions
    decorated with :func:`rest`.

    *returns_response* is determined by :func:`django_modern_rest.endpoint.rest`
    function and its parameters.

    This spec has two major ways of how it is going
    to be used depending on *returns_response* option:
    1. It is going to be used on an endpoint that returns a regular type
    2. It is going to be used on an endpoint
       that return :class:`django.http.HttpResponse` instance

    When *returns_response* is ``False`` we can't provide:
    - *return_type*
    """

    # TODO: this can be a tagged union with `Literal[True]` and `Literal[False]`
    returns_response: bool

    # Can be provided only when `returns_response` is `True`
    return_type: Any

    # Can be provided at all times:
    status_code: HTTPStatus

    def validate_for_response(self, response: HttpResponse) -> None:
        """Validates response against provided metadata."""
        assert self.returns_response, (  # noqa: S101
            'Do not run response validation if it is not expected'
        )
        if response.status_code != self.status_code:
            raise ResponseSerializationError(
                f'{response.status_code=} does not match '
                f'expected {self.status_code} status code',
            )


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar('_ResponseT', bound=HttpResponse | Awaitable[HttpResponse])


def validate(
    *,
    return_type: Any,
    status_code: HTTPStatus,
    # TODO:
    # errors
    # schema_modifications
    # headers
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
    by setting this configuration in your ``settings.py`` file:

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

    Raises:
        MissingEndpointMetadataError: When user did not specify
            some required metadata entries.

    Returns:
        The same function with ``__endpoint__``
        metadata instanse of :class:`EndpointMetadata`.
    """
    return _add_metadata(
        return_type=return_type,
        status_code=status_code,
        explicit_decorator_name='validate',
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
    # TODO:
    # errors
    # schema_modifications
    # headers
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
        status_code:
            When *status_code* is passed, always uses it for
            all responses. When not provided, we use smart inference
            based on the HTTP method name.

    Returns:
        The same function with ``__endpoint__``
        metadata instanse of :class:`EndpointMetadata`.
    """
    return _add_metadata(  # type: ignore[return-value]
        status_code=status_code,
        explicit_decorator_name='modify',
    )


def _add_metadata(  # noqa: WPS231
    *,
    return_type: Any | Empty = EmptyObj,
    status_code: HTTPStatus | Empty = EmptyObj,
    explicit_decorator_name: Literal['validate', 'modify'] | None = None,
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    # It is cheap for us to do the endpoint metadata calculation here,
    # because we do it once per module import.
    def decorator(  # noqa: WPS231
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        # I prefer this function to be complex,
        # but have everything in one place.
        # TODO: later this can be split into a class
        # if it gets even more complex.
        return_annotation = parse_return_annotation(func)
        if is_safe_subclass(return_annotation, HttpResponse):
            if explicit_decorator_name == 'modify':
                raise MissingEndpointMetadataError(
                    f'Since {func!r} returns HttpResponse, '
                    'it is not allowed to use `@modify` decorator',
                )
            if return_type is EmptyObj or status_code is EmptyObj:
                raise MissingEndpointMetadataError(
                    f'Since {func!r} returns HttpResponse, '
                    'it requires `@validate` decorator with these parameters: '
                    f'{return_type=} {status_code=}',
                )
            returns_response = True
        else:
            if explicit_decorator_name == 'validate':
                raise MissingEndpointMetadataError(
                    f'Since {func!r} returns regular data, '
                    'it is not allowed to use `@validate` decorator',
                )
            returns_response = False

        func.__endpoint__ = EndpointMetadata(  # type: ignore[attr-defined]
            returns_response=returns_response,
            return_type=(
                return_annotation
                if isinstance(return_type, Empty)
                else return_type
            ),
            status_code=(
                _infer_status_code(func)
                if isinstance(status_code, Empty)
                else status_code
            ),
        )
        return func

    return decorator


def _infer_status_code(endpoint_func: Callable[..., Any]) -> HTTPStatus:
    method = HTTPMethod(endpoint_func.__name__.upper())
    if method is HTTPMethod.POST:
        return HTTPStatus.CREATED
    return HTTPStatus.OK
