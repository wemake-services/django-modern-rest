from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, overload
from urllib.parse import urlsplit

from django.core.exceptions import DisallowedRedirect
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri
from django.utils.http import MAX_URL_REDIRECT_LENGTH

from django_modern_rest.cookies import NewCookie
from django_modern_rest.settings import Settings, resolve_setting

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

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
        ...     def get(self) -> str:
        ...         raise APIError(
        ...             self.format_error(
        ...                 'This API endpoint is not implemented yet',
        ...                 error_type=ErrorType.user_msg,
        ...             ),
        ...             status_code=HTTPStatus.NOT_FOUND,
        ...         )

    """

    def __init__(
        self,
        raw_data: _ItemT,
        *,
        status_code: HTTPStatus,
        headers: dict[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
    ) -> None:
        """Create response from parts."""
        if HTTPStatus.MULTIPLE_CHOICES <= status_code < HTTPStatus.BAD_REQUEST:
            raise DisallowedRedirect(
                'APIError should not be used with redirects, '
                'use APIRedirectError instead '
                f'with status code {status_code!s}',
            )

        super().__init__()
        self.raw_data = raw_data
        self.status_code = status_code
        self.headers = headers
        self.cookies = cookies


class APIRedirectError(Exception):
    """
    Special class to fast return redirects from API.

    We model this class closely
    to match :class:`django.http.HttpResponseRedirect`.

    Usage:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django_modern_rest import (
        ...     APIRedirectError,
        ...     Controller,
        ...     ResponseSpec,
        ...     modify,
        ...     HeaderSpec,
        ... )
        >>> from django_modern_rest.errors import ErrorType
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class UserController(Controller[PydanticSerializer]):
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
        ...         # This API endpoint is deprecated, use new one:
        ...         raise APIRedirectError(
        ...             '/api/new/users/',
        ...             status_code=HTTPStatus.FOUND,
        ...         )


    """

    # Django allows `ftp` redirects, but we don't:
    allowed_schemes: ClassVar[frozenset[str]] = frozenset(('http', 'https'))

    def __init__(
        self,
        redirect_to: '_StrOrPromise',
        *,
        status_code: HTTPStatus = HTTPStatus.FOUND,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Create redirect response from parts."""
        redirect_to = str(redirect_to)
        # This code is taken from Django's `HttpResponseRedirect`:
        if len(redirect_to) > MAX_URL_REDIRECT_LENGTH:
            raise DisallowedRedirect(
                f'Unsafe redirect exceeding {MAX_URL_REDIRECT_LENGTH} '
                'characters',
            )
        parsed = urlsplit(redirect_to)
        if parsed.scheme and parsed.scheme not in self.allowed_schemes:
            raise DisallowedRedirect(
                f'Unsafe redirect to URL with protocol {parsed.scheme!r}',
            )
        # End
        if (
            status_code >= HTTPStatus.BAD_REQUEST
            or status_code < HTTPStatus.MULTIPLE_CHOICES
        ):
            raise DisallowedRedirect(
                'APIRedirectError might be used only with 3xx statuses, '
                f'given: {status_code!s}',
            )
        super().__init__()
        self.redirect_to = redirect_to
        self.status_code = status_code
        self.headers = {'Location': iri_to_uri(redirect_to), **(headers or {})}
        self.raw_data = None  # empty response body by default


@overload
def build_response(
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    method: HTTPMethod | str,
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer: 'Renderer | None' = None,
) -> HttpResponse: ...


@overload
def build_response(
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    status_code: HTTPStatus,
    method: None = None,
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    renderer: 'Renderer | None' = None,
) -> HttpResponse: ...


def build_response(  # noqa: WPS210, WPS211
    serializer: type['BaseSerializer'],
    *,
    raw_data: Any,
    method: HTTPMethod | str | None = None,
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, NewCookie] | None = None,
    status_code: HTTPStatus | None = None,
    renderer: 'Renderer | None' = None,
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

    if renderer is None:
        # IndexError here can't happen, because we validate
        # that all endpoints have at least one configured type in settings.
        renderer = resolve_setting(
            Settings.renderers,
        )[0]
        # Needed for type checking:
        assert renderer is not None  # noqa: S101

    response_headers = {
        **({} if headers is None else headers),
        'Content-Type': renderer.content_type,
    }

    response = HttpResponse(
        content=(
            b''
            if raw_data is None
            else serializer.serialize(raw_data, renderer=renderer)
        ),
        status=status,
        headers=response_headers,
    )
    if cookies:
        for cookie_key, cookie in cookies.items():
            response.set_cookie(cookie_key, **cookie.as_dict())
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
