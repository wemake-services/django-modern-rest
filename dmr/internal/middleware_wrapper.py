import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse, HttpResponseBase

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.metadata import ResponseSpec
    from dmr.serializer import BaseSerializer

_TypeT = TypeVar('_TypeT', bound=type[Any])
_CallableAny: TypeAlias = Callable[..., Any]
MiddlewareDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
_ConverterSpec: TypeAlias = tuple[
    dict[HTTPStatus, 'ResponseSpec'],
    ResponseConverter,
]


class _ClassDecorator(Protocol):
    def __call__(self, klass: _TypeT, /) -> _TypeT: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class DecoratorWithResponses:
    """Type for decorator with responses attribute."""

    decorator: _ClassDecorator
    responses: list['ResponseSpec']

    def __call__(self, klass: _TypeT) -> _TypeT:
        """Apply the decorator to the class."""
        return self.decorator(klass)


def apply_converter(
    response: HttpResponse,
    converter: _ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_descs, converter_func = converter
    if response.status_code in response_descs:
        return converter_func(response)
    return response


def validate_middleware_response(
    controller: 'Controller[BaseSerializer]',
    response: HttpResponseBase,
    view_responses: list[HttpResponseBase],
) -> HttpResponseBase:
    """
    Validate a response that the middleware has created or replaced.

    Responses from *view_responses* were returned by the original
    ``dispatch``, so they are already validated by their endpoint.
    """
    method: str = controller.request.method  # type: ignore[assignment]
    endpoint = controller.api_endpoints.get(method)
    from_view = any(
        response is view_response for view_response in view_responses
    )
    if endpoint is None or from_view:
        return response
    return endpoint.validate_response(controller, response)


def create_sync_dispatch(
    original_dispatch: _CallableAny,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> _CallableAny:
    """Create synchronous dispatch wrapper."""

    def dispatch(  # noqa: WPS430
        self: 'Controller[BaseSerializer]',
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        if request.method and request.method not in self.api_endpoints:
            return self.handle_method_not_allowed(request.method)

        view_responses: list[HttpResponseBase] = []

        def view_callable(  # noqa: WPS430
            req: HttpRequest,
            *view_args: Any,
            **view_kwargs: Any,
        ) -> HttpResponseBase:
            view_response: HttpResponseBase = original_dispatch(
                self,
                req,
                *view_args,
                **view_kwargs,
            )
            view_responses.append(view_response)
            return view_response

        response = middleware(view_callable)(request, *args, **kwargs)
        return validate_middleware_response(
            self,
            apply_converter(response, converter),
            view_responses,
        )

    return dispatch


def create_async_dispatch(
    original_dispatch: _CallableAny,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> _CallableAny:
    """Create asynchronous dispatch wrapper."""

    async def dispatch(  # noqa: WPS430
        self: 'Controller[BaseSerializer]',
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        if request.method and request.method not in self.api_endpoints:
            return await self.handle_method_not_allowed(request.method)  # type: ignore[no-any-return, misc]

        view_responses: list[HttpResponseBase] = []

        async def remember_view_response(  # noqa: WPS430
            view_coroutine: Awaitable[HttpResponseBase],
        ) -> HttpResponseBase:
            view_response = await view_coroutine
            view_responses.append(view_response)
            return view_response

        def view_callable(  # noqa: WPS430
            req: HttpRequest,
            *view_args: Any,
            **view_kwargs: Any,
        ) -> Awaitable[HttpResponseBase]:
            # Async controllers return coroutines from `dispatch`,
            # we need to remember the response they resolve to:
            return remember_view_response(
                original_dispatch(self, req, *view_args, **view_kwargs),
            )

        response = middleware(view_callable)(request, *args, **kwargs)
        # Django middleware can be either sync or async. When we wrap an async
        # view with middleware, the middleware itself might be sync
        # (returning HttpResponse) or async (returning Awaitable[HttpResponse]).
        # We need to check the actual return type at runtime and await it only
        # if it's a coroutine/awaitable, otherwise we'd get
        # a "cannot await non-coroutine" error.
        if inspect.isawaitable(response):
            response = await response
        return validate_middleware_response(
            self,
            apply_converter(response, converter),
            view_responses,
        )

    return dispatch


def do_wrap_dispatch(
    cls: Any,
    middleware: MiddlewareDecorator,
    converter: _ConverterSpec,
) -> None:
    """Internal function to wrap dispatch in middleware."""
    original_dispatch = cls.dispatch

    if cls.is_async:
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
