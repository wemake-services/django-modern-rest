from collections.abc import Callable
from typing import Any

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.internal.middleware_wrapper import (
    DecoratorWithResponses,
    MiddlewareDecorator,
    ResponseConverter,
    TypeT,
    do_wrap_dispatch,
)
from django_modern_rest.response import ResponseDescription


def wrap_middleware(  # noqa: WPS202
    middleware: MiddlewareDecorator,
    response_description: ResponseDescription,
    *response_descriptions: ResponseDescription,
) -> Callable[[ResponseConverter], DecoratorWithResponses]:
    """
    Factory function that creates a decorator with pre-configured middleware.

    This allows creating reusable decorators with specific middleware
    and response handling.

    Args:
        middleware: Django middleware to apply
        response_description: ResponseDescription for the middleware response
        response_descriptions: Others ResponseDescription

    Returns:
        A function that takes a converter and returns a class decorator

    .. code:: python

        >>> from django.views.decorators.csrf import csrf_protect
        >>> from django.http import HttpResponse
        >>> from http import HTTPStatus
        >>> from django_modern_rest import (
        ...     Controller,
        ...     ResponseDescription,
        ...     build_response,
        ... )
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> @wrap_middleware(
        ...     csrf_protect,
        ...     ResponseDescription(
        ...         return_type=dict[str, str],
        ...         status_code=HTTPStatus.FORBIDDEN,
        ...     ),
        ... )
        ... def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        ...     return build_response(
        ...         None,
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

    def decorator_factory(  # noqa: WPS430
        converter: ResponseConverter,
    ) -> DecoratorWithResponses:
        """Create a decorator with the given converter."""
        converter_spec = (response_description, converter)

        def decorator(cls: TypeT) -> TypeT:
            do_wrap_dispatch(cls, middleware, converter_spec)
            return method_decorator(csrf_exempt, name='dispatch')(cls)

        return DecoratorWithResponses(
            decorator=decorator,
            responses=[response_description, *response_descriptions],
        )

    return decorator_factory


def dispatch_decorator(  # noqa: WPS202
    func: Callable[..., Any],
) -> Callable[[TypeT], TypeT]:
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

    .. warning::

        This will return non-json responses, without respecting your spec!
        Use with caution!

        If you want full spec support, use middleware wrappers.

    """
    return method_decorator(func, name='dispatch')
