import dataclasses
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar, final

from django.http import HttpResponse
from typing_extensions import ParamSpec

from django_modern_rest.serialization import BaseSerializer

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:
    __slots__ = ('_func',)

    _func: Callable[..., Any]

    def __init__(
        self,
        func: Callable[..., Any],
        *,  # TODO: add openapi metadata?
        serializer: type[BaseSerializer],
    ) -> None:
        if inspect.iscoroutinefunction(func):
            self._func = self._async_endpoint(func, serializer)
        else:
            self._func = self._sync_endpoint(func, serializer)

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

    # TODO: support headers, metadata, http codes, etc
    def _make_http_response(
        self,
        serializer: type[BaseSerializer],
        raw_data: Any,
    ) -> HttpResponse:
        # TODO: make response data type validation
        if isinstance(raw_data, HttpResponse):
            return raw_data
        return HttpResponse(
            serializer.to_json(raw_data),
            content_type='application/json',
        )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointSpec:
    return_type: Any


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')


def rest(
    *,
    return_type: Any,  # `type[T]` limits some type annotations
    # TODO:
    # status_code
    # errors
    # schema_modifications
    # headers
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    """
    Decorator for REST endpoints.

    Args:
        return_type: When *return_type* is passed, it means that we return
            an instance of :class:`django.http.HttpResponse` or its subclass.
            But, we still want to show the response type in OpenAPI schema
            and also want to do an extra round of validation
            to be sure that it fits the schema.

    Returns:
        The same function with ``__endpoint__`` metadata definition.
    """

    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        func.__endpoint__ = EndpointSpec(  # type: ignore[attr-defined]
            return_type=return_type,
        )
        return func

    return decorator
