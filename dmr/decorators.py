import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

from django.http import HttpRequest, HttpResponseBase
from django.utils.decorators import method_decorator

from dmr.internal.middleware_wrapper import (
    DecoratorWithResponses,
    MiddlewareDecorator,
    ResponseConverter,
    do_wrap_dispatch,
)
from dmr.metadata import ResponseSpec

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

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
        >>> from dmr import Controller, ResponseSpec
        >>> from dmr.response import build_response
        >>> from dmr.plugins.pydantic import PydanticSerializer
        >>> from dmr.errors import ErrorType, ErrorModel, format_error

        >>> @wrap_middleware(
        ...     csrf_protect,
        ...     ResponseSpec(
        ...         return_type=ErrorModel,
        ...         status_code=HTTPStatus.FORBIDDEN,
        ...     ),
        ... )
        ... def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        ...     return build_response(
        ...         PydanticSerializer,
        ...         raw_data=format_error(
        ...             'CSRF verification failed. Request aborted.',
        ...             error_type=ErrorType.user_msg,
        ...         ),
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
            return cls

        return DecoratorWithResponses(  # pyrefly: ignore[bad-specialization]
            decorator=decorator,
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

        >>> from dmr import Controller
        >>> from dmr.decorators import dispatch_decorator
        >>> from dmr.plugins.pydantic import PydanticSerializer
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
        :func:`~dmr.decorators.wrap_middleware` as well.
        Or use :func:`~dmr.decorators.endpoint_decorator`.

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

    Use it with "raw" endpoints that return regular data,
    not :class:`django.http.HttpResponse`.

    Basically, all endpoints that can be decorated with
    :func:`~dmr.endpoint.modify`.

    Example:

    .. code:: python

        >>> from http import HTTPStatus

        >>> from dmr import Controller, HeaderSpec, modify
        >>> from dmr.decorators import endpoint_decorator
        >>> from dmr.plugins.pydantic import PydanticSerializer
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
    - :func:`django.views.decorators.debug.sensitive_post_parameters`
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

        # What happens here?
        # 1. We decorate `endpoint that receives `Controller`
        #    as the first argument
        # 2. But, `original_decorator` needs `HttpRequest`
        #    as the first argument, so we pass it here explicitly
        # 3. Next, we `unwrap` the original function
        #    and pass `controller` to it. It will ignore
        #    the passed `request` and use the `controller` argument
        # But, we can't explain this with types :)
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def decorator(  # pyright: ignore[reportRedeclaration]
                self: 'Controller[BaseSerializer]',
                *args: _ParamT.args,
                **kwargs: _ParamT.kwargs,
            ) -> _ReturnT:
                return await original_decorator(  # type: ignore[no-any-return, misc]
                    _unwrap_request_param(func, self),  # type: ignore[arg-type]
                )(self.request, *args, **kwargs)

        else:

            @wraps(func)
            def decorator(
                self: 'Controller[BaseSerializer]',
                *args: _ParamT.args,
                **kwargs: _ParamT.kwargs,
            ) -> _ReturnT:
                return original_decorator(  # type: ignore[return-value]
                    _unwrap_request_param(func, self),  # type: ignore[arg-type]
                )(self.request, *args, **kwargs)

        return decorator  # type: ignore[return-value]

    return factory


def _unwrap_request_param(  # noqa: WPS234
    func: Callable[
        Concatenate['Controller[BaseSerializer]', _ParamT],
        _ReturnT,
    ],
    controller: 'Controller[BaseSerializer]',
) -> Callable[Concatenate[HttpRequest, _ParamT], _ReturnT]:
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def decorator(  # pyright: ignore[reportRedeclaration]
            request: HttpRequest,
            /,
            *args: _ParamT.args,
            **kwargs: _ParamT.kwargs,
        ) -> _ReturnT:
            return await func(controller, *args, **kwargs)  # type: ignore[no-any-return]

    else:

        @wraps(func)
        def decorator(
            request: HttpRequest,
            /,
            *args: _ParamT.args,
            **kwargs: _ParamT.kwargs,
        ) -> _ReturnT:
            return func(controller, *args, **kwargs)

    return decorator  # type: ignore[return-value]
