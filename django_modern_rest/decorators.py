from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from django.http import HttpResponseBase
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.internal.middleware_wrapper import (
    DecoratorWithResponses,
    MiddlewareDecorator,
    ResponseConverter,
    do_wrap_dispatch,
)
from django_modern_rest.response import ResponseSpec

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint
    from django_modern_rest.serialization import BaseSerializer

_TypeT = TypeVar('_TypeT', bound=type[Any])


def wrap_middleware(
    middleware: MiddlewareDecorator,
    response: ResponseSpec,
    *responses: ResponseSpec,
) -> Callable[[ResponseConverter], DecoratorWithResponses]:
    """
    Factory function that creates a decorator with pre-configured middleware.

    This allows creating reusable decorators with specific middleware
    and response handling.

    Args:
        middleware: Django middleware to apply
        response: ResponseSpec for the middleware response
        responses: Others ResponseSpec

    Returns:
        A function that takes a converter and returns a class decorator

    .. code:: python

        >>> from django.views.decorators.csrf import csrf_protect
        >>> from django.http import HttpResponse
        >>> from http import HTTPStatus
        >>> from django_modern_rest import Controller, ResponseSpec
        >>> from django_modern_rest.response import build_response
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> @wrap_middleware(
        ...     csrf_protect,
        ...     ResponseSpec(
        ...         return_type=dict[str, str],
        ...         status_code=HTTPStatus.FORBIDDEN,
        ...     ),
        ... )
        ... def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        ...     return build_response(
        ...         PydanticSerializer,
        ...         raw_data={
        ...             'detail': 'CSRF verification failed. Request aborted.'
        ...         },
        ...         status_code=HTTPStatus(response.status_code),
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

    def factory(
        converter: ResponseConverter,
    ) -> DecoratorWithResponses:
        """Create a decorator with the given converter."""
        all_descriptions = [response, *responses]
        response_dict = {desc.status_code: desc for desc in all_descriptions}
        converter_spec = (response_dict, converter)

        def decorator(cls: _TypeT) -> _TypeT:
            do_wrap_dispatch(cls, middleware, converter_spec)
            return dispatch_decorator(csrf_exempt)(cls)

        return DecoratorWithResponses(
            decorator=decorator,  # pyrefly: ignore[bad-argument-type]
            responses=all_descriptions,
        )

    return factory


def dispatch_decorator(
    func: Callable[..., Any],
) -> Callable[[_TypeT], _TypeT]:
    """
    Special helper to decorate class-based view's ``dispatch`` method.

    Use it directly on controllers, like so:

    .. code:: python

        >>> from django_modern_rest import Controller
        >>> from django_modern_rest.decorators import dispatch_decorator
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

    .. danger::

        This will return non-json responses, without respecting your spec!
        Use with caution!

        If you want full spec support, use middleware wrappers.
        You would probably want to use
        :func:`~django_modern_rest.decorators.wrap_middleware` as well.
        Or use :func:`~django_modern_rest.decorators.endpoint_decorator`.

    """
    return method_decorator(func, name='dispatch')


_ParamT = ParamSpec('_ParamT')
_ReturnT = TypeVar('_ReturnT')
_ViewT = TypeVar(
    '_ViewT',
    bound=Callable[..., HttpResponseBase | Awaitable[HttpResponseBase]],
)


def endpoint_decorator(
    original_decorator: Callable[[_ViewT], _ViewT],
) -> Callable[[Callable[_ParamT, _ReturnT]], Callable[_ParamT, _ReturnT]]:
    """
    Apply regular Django-styled decorator to a single endpoint.

    Example:

    .. code:: python

        >>> from http import HTTPStatus

        >>> from django_modern_rest import Controller, HeaderSpec, modify
        >>> from django_modern_rest.decorators import endpoint_decorator
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer
        >>> from django.contrib.auth.decorators import login_required

        >>> class MyController(Controller[PydanticSerializer]):
        ...     @endpoint_decorator(login_required())
        ...     @modify(
        ...         extra_responses=[
        ...             ResponseSpec(
        ...                 None,
        ...                 status_code=HTTPStatus.FOUND,
        ...                 headers={'Location': HeaderSpec()},
        ...             ),
        ...         ],
        ...     )
        ...     def get(self) -> str:
        ...         return 'Logged in!'

    It also works for things like:
    - :func:`django.contrib.auth.decorators.login_not_required`
    - :func:`django.contrib.auth.decorators.user_passes_test`
    - :func:`django.contrib.auth.decorators.permission_required`
    - and any other default or custom django decorator

    .. warning::

        Be careful with decorators that you apply.
        They will not escape the response validation,
        but will return unmodified responses from the original decorators.

        For example: ``login_required`` will return a redirect.
        You can describe it with the extra metadata.

    """

    def factory(
        func: Callable[_ParamT, _ReturnT],
    ) -> Callable[_ParamT, _ReturnT]:
        @wraps(func)
        def decorator(
            self: 'Blueprint[BaseSerializer]',
            *args: _ParamT.args,
            **kwargs: _ParamT.kwargs,
        ) -> _ReturnT:
            # There's no good way in telling what is going
            # on with the decorated function :(
            # So, we just keep the function type as-is.
            return original_decorator(  # type: ignore[return-value]
                func,  # type: ignore[arg-type]
            )(self.request, *args, **kwargs)

        return decorator  # type: ignore[return-value]

    return factory
