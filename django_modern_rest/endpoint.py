import dataclasses
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, final

from django.http import HttpResponse
from typing_extensions import ParamSpec

from django_modern_rest.responses import ResponseValidator
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import Empty, EmptyObj

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:
    __slots__ = ('_func', '_response_validator')

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
        self._response_validator = self.response_validator_cls(
            serializer,
            func,  # we need a func before any wrappers
        )
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
        if isinstance(raw_data, HttpResponse):
            return self._response_validator.validate_response(raw_data)
        return HttpResponse(
            serializer.to_json(
                self._response_validator.validate_content(raw_data),
            ),
            content_type='application/json',
        )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointSpec:
    """
    Endpoint metadata specification.

    Stored inside ``__endpoint__`` attribute of functions
    decorated with :func:`rest`.
    """

    return_type: Any | Empty


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')


def rest(
    *,
    # `type[T]` limits some type annotations:
    return_type: Any | Empty = EmptyObj,
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
