from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from django.http import HttpResponse

from django_modern_rest.cookies import NewCookie
from django_modern_rest.settings import Settings, resolve_setting

if TYPE_CHECKING:
    from django_modern_rest.renderers import Renderer
    from django_modern_rest.serializer import BaseSerializer

_ItemT = TypeVar('_ItemT')


class APIError(Exception, Generic[_ItemT]):
    """
    Special class to fast return errors from API.

    Does perform the regular response validation.

    You can use APIError everywhere:
    - In endpoints
    - In components when parsing something
    - In auth if you want to change the response code

    Usage:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django_modern_rest import (
        ...     APIError,
        ...     Controller,
        ...     ResponseSpec,
        ...     modify,
        ... )
        >>> from django_modern_rest.errors import ErrorType
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class UserController(Controller[PydanticSerializer]):
        ...     @modify(
        ...         extra_responses=[
        ...             ResponseSpec(
        ...                 str,
        ...                 status_code=HTTPStatus.NOT_FOUND,
        ...             ),
        ...         ],
        ...     )
        ...     def get(self, user_id: int) -> str:
        ...         if user_id < 0:
        ...             raise APIError(
        ...                 self.format_error(
        ...                     'There are no users with ids < 0',
        ...                     error_type=ErrorType.user_msg,
        ...                 ),
        ...                 status_code=HTTPStatus.NOT_FOUND,
        ...             )
        ...         return f'{user_id}@example.com'  # email

    """

    def __init__(
        self,
        raw_data: _ItemT,
        *,
        status_code: HTTPStatus,
        headers: dict[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
    ) -> None:
        super().__init__()
        self.raw_data = raw_data
        self.status_code = status_code
        self.headers = headers
        self.cookies = cookies


@overload
def build_response(
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    method: HTTPMethod | str,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer_cls: type['Renderer'] | None = None,
) -> HttpResponse: ...


@overload
def build_response(
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    status_code: HTTPStatus,
    method: None = None,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    renderer_cls: type['Renderer'] | None = None,
) -> HttpResponse: ...


def build_response(  # noqa: WPS210, WPS211
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    method: HTTPMethod | str | None = None,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer_cls: type['Renderer'] | None = None,
) -> HttpResponse:
    """
    Utility that returns the actual `HttpResponse` object from its parts.

    Does not perform extra validation, only regular response validation.
    We need this as a function, so it can be called when no endpoints exist.

    Do not use directly, prefer using
    :meth:`~django_modern_rest.controller.Controller.to_response` method.
    Unless you are using a lower-level API. Like in middlewares, for example.

    You have to provide either *method* or *status_code*.
    """
    if status_code is not None:
        status = status_code
    elif method is not None:
        status = infer_status_code(method)
    else:
        raise ValueError(
            f'Cannot pass {method=!r} and {status_code=!r} '
            'to build_response at the same time',
        )

    if renderer_cls is None:
        # IndexError here can't happen, because we validate
        # that all endpoints have at least one configured type in settings.
        renderer_cls = resolve_setting(
            Settings.renderers,
            import_string=True,
        )[0]
        # Needed for type checking:
        assert renderer_cls is not None  # noqa: S101

    response_headers = {} if headers is None else headers
    response_headers['Content-Type'] = renderer_cls.content_type

    response = HttpResponse(
        content=serializer.serialize(raw_data, renderer_cls=renderer_cls),
        status=status,
        headers=response_headers,
    )
    if cookies:
        for cookie_key, new_cookie in cookies.items():
            response.set_cookie(cookie_key, **new_cookie.as_dict())
    return response


def infer_status_code(method_name: HTTPMethod | str) -> HTTPStatus:
    """
    Infer status code based on method name.

    >>> from http import HTTPMethod
    >>> infer_status_code(HTTPMethod.POST)
    <HTTPStatus.CREATED: 201>

    >>> infer_status_code('post')
    <HTTPStatus.CREATED: 201>

    >>> infer_status_code('get')
    <HTTPStatus.OK: 200>
    """
    if isinstance(method_name, HTTPMethod):
        method = method_name
    else:
        method = HTTPMethod(method_name.upper())
    if method is HTTPMethod.POST:
        return HTTPStatus.CREATED
    return HTTPStatus.OK
