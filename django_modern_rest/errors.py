from typing import TYPE_CHECKING

from django.http import HttpResponse

from django_modern_rest.exceptions import SerializationError

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.serialization import BaseSerializer


def global_error_handler(
    controller: 'Controller[BaseSerializer]',
    exc: Exception,
) -> HttpResponse:
    """
    Global error handler for all controllers.

    It is the last item in the chain that we try:
    1. Per endpoint configuration via :func:`errors` decorator
    2. Per controller configuration via
       :attr:`django_modern_rest.controller.Conrtoller.errors` attribute
    3. This global handler, specified via the configuration

    If some exception cannot be handled, it is just reraised.

    Here's an example that will produce ``{'detail': 'inf'}``
    for any :exc:`ZeroDivisionError` in your application:

    .. code:: python

       >>> from http import HTTPStatus
       >>> from django.http import HttpResponse
       >>> from django_modern_rest.controller import Controller
       >>> from django_modern_rest.errors import global_error_handler

       >>> def custom_error_handler(
       ...     controller: Controller,
       ...     exc: Exception,
       ... ) -> HttpResponse:
       ...     if isinstance(exc, ZeroDivisionError):
       ...         return controller.to_error(
       ...             {'details': 'inf!'},
       ...             status_code=HTTPStatus.NOT_IMPLEMENTED,
       ...         )
       ...     # Call the original handler to handle default errors:
       ...     return global_error_handler(controller, exc)

       >>> # And then in your settings file:
       >>> DMR_SETTINGS = {
       ...     # Object `custom_error_handler` will also work:
       ...     'global_error_handler': 'path.to.custom_error_handler',
       ... }

    """
    if isinstance(exc, SerializationError):
        payload = {'detail': exc.args[0]}
        # TODO: this is never represented in the openapi spec / responses
        return controller.to_error(payload, status_code=exc.status_code)
    raise exc
