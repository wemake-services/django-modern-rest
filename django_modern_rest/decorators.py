import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, TypeAlias, TypeVar, cast

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.response import ResponseDescription

_TypeT = TypeVar('_TypeT', bound=type[Any])
_CallableAny: TypeAlias = Callable[..., Any]
_ViewDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
_MiddlewareDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
_ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
ConverterSpec: TypeAlias = tuple[ResponseDescription, _ResponseConverter]


@dataclass(frozen=True, slots=True, kw_only=True)
class _DecoratorWithResponses:
    """Type for decorator with responses attribute."""

    decorator: Callable[[Any], Any]
    responses: list[ResponseDescription]

    def __call__(self, klass: _TypeT) -> _TypeT:
        return cast(_TypeT, self.decorator(klass))


def _apply_converter(
    response: HttpResponse,
    converter: ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_desc, converter_func = converter
    if response.status_code == response_desc.status_code:
        return converter_func(response)
    return response


def _create_sync_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: _MiddlewareDecorator,
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
        return _apply_converter(response, converter)

    return dispatch


def _create_async_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: _MiddlewareDecorator,
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
        response = middleware(view_callable)(request, *args, **kwargs)
        if inspect.isawaitable(response):
            response = await response
        return _apply_converter(response, converter)

    return dispatch


def _do_wrap_dispatch(
    cls: Any,
    middleware: _MiddlewareDecorator,
    converter: ConverterSpec,
) -> None:
    """Internal function to wrap dispatch in middleware."""
    original_dispatch = cls.dispatch
    is_async = getattr(cls, 'view_is_async', False)

    if is_async:
        cls.dispatch = _create_async_dispatch(
            original_dispatch,
            middleware,
            converter,
        )
    else:
        cls.dispatch = _create_sync_dispatch(
            original_dispatch,
            middleware,
            converter,
        )


def wrap_middleware_factory(  # noqa: WPS202
    middleware: _MiddlewareDecorator,
    response_description: ResponseDescription,
) -> Callable[[_ResponseConverter], _DecoratorWithResponses]:
    """
    Factory function that creates a decorator with pre-configured middleware.

    This allows creating reusable decorators with specific middleware
    and response handling.

    Args:
        middleware: Django middleware to apply
        response_description: ResponseDescription for the middleware response

    Returns:
        A function that takes a converter and returns a class decorator

    .. code:: python

        >>> from django.views.decorators.csrf import csrf_protect
        >>> from django.http import JsonResponse, HttpResponse
        >>> from http import HTTPStatus
        >>> from django_modern_rest import Controller, ResponseDescription
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> @wrap_middleware_factory(
        ...     csrf_protect,
        ...     ResponseDescription(
        ...         return_type=dict[str, str],
        ...         status_code=HTTPStatus.FORBIDDEN,
        ...     ),
        ... )
        ... def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        ...     return JsonResponse(
        ...         {'detail': 'CSRF verification failed. Request aborted.'},
        ...         status=HTTPStatus.FORBIDDEN,
        ...     )

        >>> @csrf_protect_json
        ... class MyController(Controller[PydanticSerializer]):
        ...     responses = [
        ...         *csrf_protect_json.responses,
        ...     ]
        ...
        ...     def post(self) -> dict[str, str]:
        ...         return {'message': 'ok'}
    """

    def decorator_factory(  # noqa: WPS430
        converter: _ResponseConverter,
    ) -> _DecoratorWithResponses:
        """Create a decorator with the given converter."""
        converter_spec = (response_description, converter)

        def decorator(cls: _TypeT) -> _TypeT:
            _do_wrap_dispatch(cls, middleware, converter_spec)
            return method_decorator(csrf_exempt, name='dispatch')(cls)

        return _DecoratorWithResponses(
            decorator=decorator,
            responses=[response_description],
        )

    return decorator_factory


def dispatch_decorator(  # noqa: WPS202
    func: Callable[..., Any],
) -> Callable[[_TypeT], _TypeT]:
    """
    Special helper to decorate class-based view's ``dispatch`` method.

    Use it directly on controllers, like so:

    .. code:: python

        >>> from django_modern_rest import dispatch_decorator, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer
        >>> from django.contrib.auth.decorators import login_required

        >>> @dispatch_decorator(login_required())
        ... class MyController(Controller[PydanticSerializer]):
        ...     def get(self) -> str:
        ...         return 'Logged in!'

    In this example we would require all calls
    to all methods of ``MyController`` to require an existing authentication.

    It also works for things like:
    - :func:`django.contrib.auth.decorators.login_not_required`
    - :func:`django.contrib.auth.decorators.user_passes_test`
    - :func:`django.contrib.auth.decorators.permission_required`
    - and any other default or custom django decorator

    """
    return method_decorator(func, name='dispatch')
