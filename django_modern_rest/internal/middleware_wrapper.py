import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from django_modern_rest.metadata import ResponseSpec

_TypeT = TypeVar('_TypeT', bound=type[Any])
_CallableAny: TypeAlias = Callable[..., Any]
MiddlewareDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
_ConverterSpec: TypeAlias = tuple[
    dict[HTTPStatus, 'ResponseSpec'],
    ResponseConverter,
]
_ViewDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]


@dataclass(frozen=True, slots=True, kw_only=True)
class DecoratorWithResponses:
    """Type for decorator with responses attribute."""

    decorator: Callable[[_TypeT], _TypeT]  # pyright: ignore[reportGeneralTypeIssues]
    responses: list['ResponseSpec']

    def __call__(self, klass: _TypeT) -> _TypeT:
        """Apply the decorator to the class."""
        # pyrefly: ignore [bad-argument-type, bad-return]
        return self.decorator(klass)  # pyright: ignore[reportReturnType]


def apply_converter(
    response: HttpResponse,
    converter: _ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_descs, converter_func = converter
    if response.status_code in response_descs:
        return converter_func(response)
    return response


def create_sync_dispatch(
    original_dispatch: _CallableAny,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> _CallableAny:
    """Create synchronous dispatch wrapper."""

    def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        if request.method not in self.api_endpoints:
            return self.handle_method_not_allowed(request.method)  # type: ignore[no-any-return]

        def view_callable(  # noqa: WPS430
            req: HttpRequest,
            *view_args: Any,
            **view_kwargs: Any,
        ) -> HttpResponse:
            return original_dispatch(self, req, *view_args, **view_kwargs)  # type: ignore[no-any-return]

        response = middleware(view_callable)(request, *args, **kwargs)
        return apply_converter(response, converter)

    return dispatch


def create_async_dispatch(
    original_dispatch: _CallableAny,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> _CallableAny:
    """Create asynchronous dispatch wrapper."""

    async def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        if request.method not in self.api_endpoints:
            return await self.handle_method_not_allowed(request.method)  # type: ignore[no-any-return]

        def view_callable(  # noqa: WPS430
            req: HttpRequest,
            *view_args: Any,
            **view_kwargs: Any,
        ) -> HttpResponse:
            return original_dispatch(self, req, *view_args, **view_kwargs)  # type: ignore[no-any-return]

        response: HttpResponse | Awaitable[HttpResponse] = middleware(
            view_callable,
        )(request, *args, **kwargs)
        # Django middleware can be either sync or async. When we wrap an async
        # view with middleware, the middleware itself might be sync
        # (returning HttpResponse) or async (returning Awaitable[HttpResponse]).
        # We need to check the actual return type at runtime and await it only
        # if it's a coroutine/awaitable, otherwise we'd get
        # "cannot await non-coroutine" error.
        if inspect.isawaitable(response):
            response = await response
        return apply_converter(response, converter)

    return dispatch


def do_wrap_dispatch(
    cls: Any,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> None:
    """Internal function to wrap dispatch in middleware."""
    original_dispatch = cls.dispatch
    is_async = cls.view_is_async

    if is_async:
        cls.dispatch = create_async_dispatch(
            original_dispatch,
            middleware,
            converter,
        )
    else:
        cls.dispatch = create_sync_dispatch(
            original_dispatch,
            middleware,
            converter,
        )
