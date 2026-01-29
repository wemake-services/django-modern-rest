import dataclasses
from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import Any, Generic, TypeVar, overload

from django.http import HttpResponse

from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.headers import HeaderSpec, NewHeader
from django_modern_rest.renderers import Renderer
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import Settings, resolve_setting

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
        ...                 'There are no users with ids < 0',
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
    ) -> None:
        """Create response from parts."""
        super().__init__()
        self.raw_data = raw_data
        self.status_code = status_code
        self.headers = headers


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseSpec:
    """
    Represents a single API response specification.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response.
        cookies: Shows *cookies* in the documentation.
            When passed, we validate that all given required cookies are present
            in the final response.

    We use this structure to validate responses and render them in OpenAPI.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus = dataclasses.field(kw_only=True)
    headers: Mapping[str, HeaderSpec] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    cookies: Mapping[str, CookieSpec] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )

    # TODO: description, examples, etc


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ResponseModification:
    """
    Represents a single API modification.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            Headers passed here will be added to the final response.
        cookies: Shows *cookies* in the documentation.
            Cookies passed here will be added to the final response.

    We use this structure to modify the default response.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus
    headers: Mapping[str, NewHeader] | None
    cookies: Mapping[str, NewCookie] | None

    def to_spec(self) -> ResponseSpec:
        """Convert response modification to response description."""
        return ResponseSpec(
            return_type=self.return_type,
            status_code=self.status_code,
            headers=(
                None
                if self.headers is None
                else {
                    header_name: header.to_spec()
                    for header_name, header in self.headers.items()
                }
            ),
            cookies=(
                None
                if self.cookies is None
                else {
                    cookie_key: cookie.to_spec()
                    for cookie_key, cookie in self.cookies.items()
                }
            ),
        )


@overload
def build_response(
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    method: HTTPMethod | str,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer_cls: type[Renderer] | None = None,
) -> HttpResponse: ...


@overload
def build_response(
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    status_code: HTTPStatus,
    method: None = None,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    renderer_cls: type[Renderer] | None = None,
) -> HttpResponse: ...


def build_response(  # noqa: WPS210, WPS211
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    method: HTTPMethod | str | None = None,
    headers: dict[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer_cls: type[Renderer] | None = None,
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
