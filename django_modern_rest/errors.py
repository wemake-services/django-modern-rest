import enum
import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    NotRequired,
    TypeAlias,
    final,
    overload,
)

from django.http import HttpResponse
from typing_extensions import TypedDict

from django_modern_rest.exceptions import (
    NotAcceptableError,
    NotAuthenticatedError,
    SerializationError,
    ValidationError,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serializer import BaseSerializer


@final
@enum.unique
class ErrorType(enum.StrEnum):
    """
    Collection of all possible error types that we use in DMR.

    Attributes:
        value_error: Raised when we can't parse something.
        not_allowed: Raised when using unsupported http method. 405 alias.
        security: Raised when security related error happens.
        user_msg: Raised for custom errors from users.

    """

    value_error = 'value_error'
    not_allowed = 'not_allowed'
    security = 'security'
    user_msg = 'user_msg'


class ErrorDetail(TypedDict):
    """Base schema for error details description."""

    msg: str
    type: NotRequired[str]
    loc: NotRequired[list[int | str]]


class ErrorModel(TypedDict):
    """
    Default error response schema.

    Can be customized. To do that:

    1. Subclass the needed serailizer
    2. Define new error model
    3. Set ``error_model`` of your custom serializer to this new schema
    4. Override
       :meth:`django_modern_rest.serialization.BaseSerializer.error_serialize`
       method

    Done!
    """

    detail: list[ErrorDetail]


#: Error handler type for sync callbacks.
SyncErrorHandler: TypeAlias = Callable[
    ['Endpoint', 'Controller[BaseSerializer]', Exception],  # noqa: WPS226
    HttpResponse,
]

#: Error handler type for async callbacks.
AsyncErrorHandler: TypeAlias = Callable[
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
def wrap_handler(method: _MethodSyncHandler) -> SyncErrorHandler: ...


@overload
def wrap_handler(method: _MethodAsyncHandler) -> AsyncErrorHandler: ...


def wrap_handler(
    method: _MethodSyncHandler | _MethodAsyncHandler,
) -> SyncErrorHandler | AsyncErrorHandler:
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


# NOTE: keep this in sync with `BaseSerializer.error_serialize`
_default_handled_excs: Final = (
    SerializationError,
    NotAuthenticatedError,
    NotAcceptableError,
    ValidationError,
)


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

    Here's an example that will produce
    ``{'detail': [{'msg': 'inf', 'type': 'user_msg'}]}``
    for any :exc:`ZeroDivisionError` in your application:

    .. code:: python

       >>> from http import HTTPStatus
       >>> from django.http import HttpResponse
       >>> from django_modern_rest.controller import Controller
       >>> from django_modern_rest.endpoint import Endpoint
       >>> from django_modern_rest.errors import global_error_handler, ErrorType

       >>> def custom_error_handler(
       ...     controller: Controller,
       ...     endpoint: Endpoint,
       ...     exc: Exception,
       ... ) -> HttpResponse:
       ...     if isinstance(exc, ZeroDivisionError):
       ...         return controller.to_error(
       ...             controller.serializer.error_serialize(
       ...                 'inf',
       ...                 error_type=ErrorType.user_msg,
       ...             ),
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
    if isinstance(exc, _default_handled_excs):
        return controller.to_error(
            controller.serializer.error_serialize(exc),
            status_code=exc.status_code,
        )
    raise  # noqa: PLE0704
