from collections.abc import Awaitable, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
)

from django.http import HttpResponse

from django_modern_rest.exceptions import (
    NotAuthenticatedError,
    SerializationError,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint
    from django_modern_rest.endpoint import Endpoint


#: Error handler type for sync callbacks.
SyncErrorHandlerT: TypeAlias = Callable[
    [Any, 'Endpoint', Exception],  # this is not `Any`, but mypy can't do better
    HttpResponse,
]

#: Error handler type for async callbacks.
AsyncErrorHandlerT: TypeAlias = Callable[
    [Any, 'Endpoint', Exception],  # this is not `Any`, but mypy can't do better
    Awaitable[HttpResponse],
]


def global_error_handler(
    controller: 'Blueprint[Any]',
    endpoint: 'Endpoint',
    exc: Exception,
) -> HttpResponse:
    """
    Global error handler for all cases.

    It is the last item in the chain that we try:

    1. Per endpoint configuration via
       :meth:`~django_modern_rest.endpoint.Endpoint.handle_error`
       and :meth:`~django_modern_rest.endpoint.Endpoint.handle_async_error`
       methods
    2. This global handler, specified via the configuration

    If some exception cannot be handled, it is just reraised.

    Args:
        controller: Controller instance that *endpoint* belongs to.
        endpoint: Endpoint where error happened.
        exc: Exception instance that happened.

    Returns:
        :class:`~django.http.HttpResponse` with proper response for this error.
        Or raise *exc* back.

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
       ...             {'details': 'inf!'},  # TODO: replace with new API
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
