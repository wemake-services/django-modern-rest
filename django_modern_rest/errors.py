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
    InternalServerError,
    NotAcceptableError,
    NotAuthenticatedError,
    RequestSerializationError,
    ResponseSchemaError,
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

    Can be customized.
    See :ref:`customizing-error-messages` for more details.
    """

    detail: list[ErrorDetail]


def format_error(  # noqa: C901, WPS231
    error: str | Exception,
    *,
    loc: str | None = None,
    error_type: str | ErrorType | None = None,
) -> ErrorModel:
    """
    Convert error to the common format.

    Default implementation.

    Args:
        error: A serialization exception like a validation error or
            a ``django_modern_rest.exceptions.DataParsingError``.
        loc: Location where this error happened.
            Like "headers" or "field_name".
        error_type: Optional type of the error for extra metadata.

    Returns:
        Simple python object - exception converted to a common format.

    """
    # NOTE: keep this function in sync with `_default_handled_excs`
    from django.conf import settings  # noqa: PLC0415

    if isinstance(error, ValidationError):
        return {'detail': error.payload}

    if isinstance(
        error,
        (
            RequestSerializationError,
            ResponseSchemaError,
            NotAcceptableError,
            NotAuthenticatedError,
        ),
    ):
        error_type = (
            ErrorType.security
            if isinstance(error, NotAuthenticatedError)
            else ErrorType.value_error
        )
        error = str(error.args[0])

    if isinstance(error, str):
        msg: ErrorDetail = {'msg': error}
        if loc is not None:
            msg.update({'loc': [loc]})
        if error_type is not None:
            msg.update({'type': str(error_type)})
        return {'detail': [msg]}

    if isinstance(error, InternalServerError):
        return {
            'detail': [
                {
                    'msg': str(error)
                    if settings.DEBUG
                    else InternalServerError.default_message,
                },
            ],
        }

    raise NotImplementedError(
        f'Cannot format error {error!r} of type {type(error)} safely',
    )


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


# NOTE: keep this tuple in sync with `format_error()`
_default_handled_excs: Final = (
    RequestSerializationError,
    ResponseSchemaError,  # can only happen if validation is enabled
    NotAuthenticatedError,
    NotAcceptableError,
    ValidationError,
    InternalServerError,
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
       ...             controller.format_error(
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
            controller.format_error(exc),
            status_code=exc.status_code,
        )
    raise  # noqa: PLE0704
