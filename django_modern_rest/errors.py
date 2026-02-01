import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    overload,
)

from django.http import HttpResponse

from django_modern_rest.exceptions import (
    NotAuthenticatedError,
    SerializationError,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serialization import BaseSerializer

#: Error handler type for sync callbacks.
SyncErrorHandlerT: TypeAlias = Callable[
    ['Endpoint', 'Controller[BaseSerializer]', Exception],  # noqa: WPS226
    HttpResponse,
]

#: Error handler type for async callbacks.
AsyncErrorHandlerT: TypeAlias = Callable[
    ['Endpoint', 'Controller[BaseSerializer]', Exception],
    Awaitable[HttpResponse],
]


_MethodSyncHandler: TypeAlias = Callable[
    # This is not `Any`, this a `Blueprint[BaseSerializer]` instance,
    # but mypy can't do better:
    ['Any', 'Endpoint', 'Controller[Any]', Exception],
    HttpResponse,
]

_MethodAsyncHandler: TypeAlias = Callable[
    # This is not `Any`, this a `Blueprint[BaseSerializer]` instance,
    # but mypy can't do better:
    ['Any', 'Endpoint', 'Controller[Any]', Exception],
    Awaitable[HttpResponse],
]


@overload
def wrap_handler(method: _MethodSyncHandler) -> SyncErrorHandlerT: ...


@overload
def wrap_handler(method: _MethodAsyncHandler) -> AsyncErrorHandlerT: ...


def wrap_handler(
    method: _MethodSyncHandler | _MethodAsyncHandler,
) -> SyncErrorHandlerT | AsyncErrorHandlerT:
    """
    Utility function to wrap controller / blueprint methods.

    It is used to wrap an existing controller method
    and pass it as ``error_handler=`` argument to an endpoint.
    """
    if inspect.iscoroutinefunction(method):

        @wraps(method)
        async def decorator(  # noqa: WPS430  # pyright: ignore[reportRedeclaration]
            endpoint: 'Endpoint',
            controller: 'Controller[BaseSerializer]',
            exc: Exception,
        ) -> HttpResponse:
            return await method(  # type: ignore[no-any-return]
                controller.active_blueprint,
                endpoint,
                controller,
                exc,
            )

    else:

        @wraps(method)  # pyrefly: ignore[bad-argument-type]
        def decorator(  # noqa: WPS430
            endpoint: 'Endpoint',
            controller: 'Controller[BaseSerializer]',
            exc: Exception,
        ) -> HttpResponse:
            return method(  # type: ignore[return-value]
                controller.active_blueprint,
                endpoint,
                controller,
                exc,
            )

    return decorator


def global_error_handler(
    endpoint: 'Endpoint',
    controller: 'Controller[BaseSerializer]',
    exc: Exception,
) -> HttpResponse:
    """
    Global error handler for all cases.

    It is the last item in the chain that we try:

    1. Per endpoint configuration via
       :meth:`~django_modern_rest.endpoint.Endpoint.handle_error`
       and :meth:`~django_modern_rest.endpoint.Endpoint.handle_async_error`
       methods
    2. Per blueprint handlers
    3. Per controller handlers
    4. This global handler, specified via the configuration

    If some exception cannot be handled, it is just reraised.

    Args:
        endpoint: Endpoint where error happened.
        controller: Controller instance that *endpoint* belongs to.
        exc: Exception instance that happened.

    Returns:
        :class:`~django.http.HttpResponse` with proper response for this error.
        Or raise *exc* back.

    You can access active blueprint
    via :attr:`~django_modern_rest.controller.Controller.active_blueprint`.

    Here's an example that will produce ``{'detail': 'inf'}``
    for any :exc:`ZeroDivisionError` in your application:

    .. code:: python

       >>> from http import HTTPStatus
       >>> from django.http import HttpResponse
       >>> from django_modern_rest.controller import Controller
       >>> from django_modern_rest.endpoint import Endpoint
       >>> from django_modern_rest.errors import global_error_handler

       >>> def custom_error_handler(
       ...     controller: Controller,
       ...     endpoint: Endpoint,
       ...     exc: Exception,
       ... ) -> HttpResponse:
       ...     if isinstance(exc, ZeroDivisionError):
       ...         return controller.to_error(
       ...             {'detail': 'inf!'},  # TODO: replace with new API
       ...             status_code=HTTPStatus.NOT_IMPLEMENTED,
       ...         )
       ...     # Call the original handler to handle default errors:
       ...     return global_error_handler(controller, endpoint, exc)

       >>> # And then in your settings file:
       >>> DMR_SETTINGS = {
       ...     # Object `custom_error_handler` will also work:
       ...     'global_error_handler': 'path.to.custom_error_handler',
       ... }

    .. warning::

        Make sure you always call original ``global_error_handler``
        in the very end. Unless, you want to disable original error handling.

    """
    from django_modern_rest.negotiation import request_renderer  # noqa: PLC0415

    if isinstance(exc, (SerializationError, NotAuthenticatedError)):
        renderer_cls = request_renderer(
            controller.request,
        ) or endpoint.response_negotiator(controller.request)
        # TODO: unify, all errors must be the same
        payload = (
            controller.serializer.error_serialize(exc.args[0])
            if isinstance(exc, NotAuthenticatedError)
            else exc.args[0]
        )
        return controller.to_error(
            # TODO: validate error response's schema
            {'detail': payload},
            status_code=exc.status_code,
            renderer_cls=renderer_cls,
        )
    raise exc
