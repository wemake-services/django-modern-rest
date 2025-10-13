import dataclasses
import inspect
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, final

from django.http import HttpResponse
from typing_extensions import ParamSpec

from django_modern_rest.responses import ResponseValidator
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import Empty, EmptyObj

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Endpoint:
    __slots__ = ('_func', '_metadata', '_method', 'response_validator')

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
        self._method = func.__name__.lower()
        self._metadata: EndpointSpec | Empty = getattr(
            func,
            '__endpoint__',
            EmptyObj,
        )
        self.response_validator = self.response_validator_cls(
            serializer,
            func,  # we need a func before any wrappers
            metadata=self._metadata,
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

    # TODO: support headers, metadata, etc
    def _make_http_response(
        self,
        serializer: type[BaseSerializer],
        raw_data: Any,
    ) -> HttpResponse:
        if isinstance(raw_data, HttpResponse):
            return self.response_validator.validate_response(raw_data)
        return HttpResponse(
            content=serializer.to_json(
                self.response_validator.validate_content(raw_data),
            ),
            content_type='application/json',
            status=self._infer_status_code(),
        )

    def _infer_status_code(self) -> int:
        if not isinstance(self._metadata, Empty) and not isinstance(
            self._metadata.status_code,
            Empty,
        ):
            return self._metadata.status_code
        if self._method == 'post':
            return HTTPStatus.CREATED
        return HTTPStatus.OK


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointSpec:
    """
    Endpoint metadata specification.

    Stored inside ``__endpoint__`` attribute of functions
    decorated with :func:`rest`.
    """

    return_type: Any | Empty
    status_code: HTTPStatus | Empty


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')


def rest(
    *,
    # `type[T]` limits some type annotations:
    return_type: Any | Empty = EmptyObj,
    status_code: HTTPStatus | Empty = EmptyObj,
    # TODO:
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
        status_code: When *status_code* is passed, always uses it for
            all responses. When not provided, uses smart inference
            based on the HTTP method name.

    Returns:
        The same function with ``__endpoint__`` metadata definition.
    """

    def decorator(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        func.__endpoint__ = EndpointSpec(  # type: ignore[attr-defined]
            return_type=return_type,
            status_code=status_code,
        )
        return func

    return decorator
