from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal, Never, overload

from django.http import HttpRequest, HttpResponseBase
from typing_extensions import ParamSpec, Protocol, TypeVar, deprecated

if TYPE_CHECKING:
    from dmr.endpoint import Endpoint


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ResponseT = TypeVar(
    '_ResponseT',
    bound=HttpResponseBase | Awaitable[HttpResponseBase],
)


class ModifySyncCallable(Protocol):
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
        'Passing sync `error_handler` to `@modify` requires sync endpoint',
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


class ModifyAsyncCallable(Protocol):
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


class ModifyAnyCallable(Protocol):
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
def request_endpoint(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> 'Endpoint': ...


@overload
def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Endpoint | None': ...


def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Endpoint | None':
    """
    Return an instance of the ``Endpoint`` that was used for this request.

    When *strict* is passed and *request* has no endpoint,
    we raise :exc:`AttributeError`.
    This can happen for ``405`` responses, for example.
    They don't have endpoints. All others do.

    .. versionadded:: 0.7.0
    """
    endpoint = getattr(request, '__dmr_endpoint__', None)
    if endpoint is None and strict:
        raise AttributeError('__dmr_endpoint__')
    return endpoint
