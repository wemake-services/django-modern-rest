import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from django_modern_rest.response import ResponseDescription

TypeT = TypeVar('TypeT', bound=type[Any])
_CallableAny: TypeAlias = Callable[..., Any]
MiddlewareDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
_ConverterSpec: TypeAlias = tuple['ResponseDescription', ResponseConverter]
_ViewDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]


@dataclass(frozen=True, slots=True, kw_only=True)
class DecoratorWithResponses:
    """Type for decorator with responses attribute."""

    decorator: Callable[[Any], Any]
    responses: list['ResponseDescription']

    def __call__(self, klass: TypeT) -> TypeT:
        """Apply the decorator to the class."""
        return self.decorator(klass)  # type: ignore[no-any-return]


def apply_converter(
    response: HttpResponse,
    converter: _ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_desc, converter_func = converter
    if response.status_code == response_desc.status_code:
        return converter_func(response)
    return response


def create_sync_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> Callable[..., HttpResponse]:
    """Create synchronous dispatch wrapper."""

    def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
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
    original_dispatch: Callable[..., Any],
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> Callable[..., Any]:
    """Create asynchronous dispatch wrapper."""

    async def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        def view_callable(  # noqa: WPS430
            req: HttpRequest,
            *view_args: Any,
            **view_kwargs: Any,
        ) -> HttpResponse:
            return original_dispatch(self, req, *view_args, **view_kwargs)  # type: ignore[no-any-return]

        response: HttpResponse | Awaitable[HttpResponse] = middleware(
            view_callable,
        )(request, *args, **kwargs)
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
