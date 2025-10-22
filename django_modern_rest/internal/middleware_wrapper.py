from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar, cast

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from django_modern_rest.response import ResponseDescription

TypeT = TypeVar('TypeT', bound=type[Any])
CallableAny: TypeAlias = Callable[..., Any]
MiddlewareDecorator: TypeAlias = Callable[[CallableAny], CallableAny]
ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
ConverterSpec: TypeAlias = tuple['ResponseDescription', ResponseConverter]
ViewDecorator: TypeAlias = Callable[[CallableAny], CallableAny]


@dataclass(frozen=True, slots=True, kw_only=True)
class DecoratorWithResponses:
    """Type for decorator with responses attribute."""

    decorator: Callable[[Any], Any]
    responses: list['ResponseDescription']

    def __call__(self, klass: TypeT) -> TypeT:
        """Wrap for cast types."""
        return cast(TypeT, self.decorator(klass))


def apply_converter(
    response: HttpResponse,
    converter: ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_desc, converter_func = converter
    if response.status_code == response_desc.status_code:
        return converter_func(response)
    return response


def create_sync_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: MiddlewareDecorator,
    converter: ConverterSpec,
) -> Callable[..., HttpResponse]:
    """Create synchronous dispatch wrapper."""

    def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        view_callable = partial(original_dispatch, self)
        response = middleware(view_callable)(request, *args, **kwargs)
        return apply_converter(response, converter)

    return dispatch


def create_async_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: MiddlewareDecorator,
    converter: ConverterSpec,
) -> Callable[..., Any]:
    """Create asynchronous dispatch wrapper."""

    async def dispatch(  # noqa: WPS430
        self: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        view_callable = partial(original_dispatch, self)
        response: HttpResponse | Awaitable[HttpResponse] = middleware(
            view_callable,
        )(request, *args, **kwargs)
        if isinstance(response, Awaitable):
            response = await response
        return apply_converter(response, converter)

    return dispatch


def do_wrap_dispatch(
    cls: Any,
    middleware: MiddlewareDecorator,
    converter: ConverterSpec,
) -> None:
    """Internal function to wrap dispatch in middleware."""
    original_dispatch = cls.dispatch
    is_async = getattr(cls, 'view_is_async', False)

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
