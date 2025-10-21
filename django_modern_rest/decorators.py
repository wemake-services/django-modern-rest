import inspect
from collections.abc import Callable
from functools import partial
from typing import Any, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.response import ResponseDescription

_TypeT = TypeVar('_TypeT', bound=type[Any])
_CallableAny: TypeAlias = Callable[..., Any]
_ViewDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
_MiddlewareDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]
_ResponseConverter: TypeAlias = Callable[[HttpResponse], HttpResponse]
_ConverterSpec: TypeAlias = tuple[ResponseDescription, _ResponseConverter]


def _apply_converter(
    response: HttpResponse,
    converter: _ConverterSpec,
) -> HttpResponse:
    """Apply response converter based on status code matching."""
    response_desc, converter_func = converter
    if response.status_code == response_desc.status_code:
        return converter_func(response)
    return response


def _create_sync_dispatch(
    original_dispatch: Callable[..., Any],
    middleware: _MiddlewareDecorator,
    converter: _ConverterSpec,
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
    converter: _ConverterSpec,
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
    converter: _ConverterSpec,
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


def wrap_middleware(
    middleware: _MiddlewareDecorator,
    converter: _ConverterSpec,
) -> Callable[[_TypeT], _TypeT]:
    """
    Wrap controller dispatch with middleware and response converter.

    This decorator applies Django middleware to a controller and allows
    converting middleware responses based on status code.

    Args:
        middleware: Django middleware to apply
        converter: Tuple of (ResponseDescription, converter_function).
            When middleware returns a response matching the status_code,
            the converter function is called to transform it.

    .. code:: python
        >>> from django.views.decorators.csrf import csrf_protect
        >>> from django.http import JsonResponse
        >>> from http import HTTPStatus
        >>> from django_modern_rest import Controller, ResponseDescription
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer
        >>>
        >>> @wrap_middleware(
        ...     csrf_protect,
        ...     converter=(
        ...         ResponseDescription(
        ...             return_type=dict[str, str],
        ...             status_code=HTTPStatus.FORBIDDEN,
        ...         ),
        ...         lambda resp: JsonResponse(
        ...             {'detail': 'CSRF failed'},
        ...             status=HTTPStatus.FORBIDDEN,
        ...         ),
        ...     ),
        ... )
        ... class MyController(Controller[PydanticSerializer]):
        ...     def post(self) -> dict[str, str]:
        ...         return {'message': 'ok'}

    """

    def decorator(cls: _TypeT) -> _TypeT:
        _do_wrap_dispatch(cls, middleware, converter)
        return method_decorator(csrf_exempt, name='dispatch')(cls)

    return decorator


def dispatch_decorator(
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
