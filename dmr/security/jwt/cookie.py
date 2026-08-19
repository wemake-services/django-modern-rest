from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, Self

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.internal.csrf import ensure_csrf
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.jwt.auth import JWTAsyncAuth, JWTSyncAuth
from dmr.security.jwt.token import JWToken

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

#: Default name of the cookie that stores the access token.
DEFAULT_ACCESS_COOKIE: Final = 'access_token'

#: Default name of the cookie that stores the refresh token.
DEFAULT_REFRESH_COOKIE: Final = 'refresh_token'


class _BaseCookieJWTAuth(ResponseSpecProvider):
    __slots__ = ()

    security_scheme_name: str
    cookie_name: str

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.cookie_name,
                security_scheme_in='cookie',
                description='JWT token auth via cookie',
            ),
        }

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Declare extra responses for cookie auth + CSRF checks."""
        return [
            *self._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=NotAuthenticatedError.status_code,
                    description='Raised when auth was not successful',
                ),
                existing_responses,
            ),
            *self._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=HTTPStatus.FORBIDDEN,
                    description='Raised when CSRF check failed',
                ),
                existing_responses,
            ),
        ]

    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Read the raw jwt token from a cookie."""
        return request.COOKIES.get(self.cookie_name)

    def split_encoded_token(self, header: str) -> str | None:
        """
        Cookies store the encoded token as-is.

        Unlike the ``Authorization`` header, a cookie value has no
        ``Bearer`` prefix to strip.
        """
        return header or None

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        # CSRF is only enforced when the cookie is actually present.
        # Otherwise a request that carries no cookie at all could not
        # fall through to the next auth in the chain.
        if self.get_token_from_request(controller.request):
            ensure_csrf(controller)


class CookieJWTSyncAuth(_BaseCookieJWTAuth, JWTSyncAuth):
    """
    Sync jwt auth reading the token from a cookie.

    CSRF is automatically enforced whenever the cookie is present.

    .. warning::

        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts. Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.

    .. warning::

        Always issue this cookie with ``httponly=True`` and ``secure=True``
        in production, otherwise the token is readable by any script
        running on the page and can leak over plain HTTP.

    .. versionadded:: 0.15.0
    """

    __slots__ = ('cookie_name',)

    def __init__(  # noqa: WPS211
        self,
        *,
        cookie_name: str = DEFAULT_ACCESS_COOKIE,
        user_id_field: str = 'pk',
        algorithm: str = 'HS256',
        security_scheme_name: str = 'jwt',
        secret: str | None = None,
        token_cls: type[JWToken] = JWToken,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_expiry: bool = True,
        verify_issued_at: bool = True,
        verify_jwt_id: bool = True,
        verify_not_before: bool = True,
        verify_subject: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        Same as :class:`~dmr.security.jwt.auth.JWTSyncAuth`,
        but *cookie_name* replaces ``auth_header`` and ``auth_scheme``,
        because cookies store the encoded token without any prefix.
        """
        super().__init__(
            user_id_field=user_id_field,
            algorithm=algorithm,
            security_scheme_name=security_scheme_name,
            secret=secret,
            token_cls=token_cls,
            leeway=leeway,
            accepted_audiences=accepted_audiences,
            accepted_issuers=accepted_issuers,
            require_claims=require_claims,
            verify_expiry=verify_expiry,
            verify_issued_at=verify_issued_at,
            verify_jwt_id=verify_jwt_id,
            verify_not_before=verify_not_before,
            verify_subject=verify_subject,
            strict_audience=strict_audience,
            enforce_minimum_key_length=enforce_minimum_key_length,
        )
        self.cookie_name = cookie_name

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Enforce CSRF, then authenticate via the cookie token."""
        self._ensure_csrf(controller)
        return super().__call__(endpoint, controller)


class CookieJWTAsyncAuth(_BaseCookieJWTAuth, JWTAsyncAuth):
    """
    Async jwt auth reading the token from a cookie.

    CSRF is automatically enforced whenever the cookie is present.

    .. warning::

        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts. Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.

    .. warning::

        Always issue this cookie with ``httponly=True`` and ``secure=True``
        in production, otherwise the token is readable by any script
        running on the page and can leak over plain HTTP.

    .. versionadded:: 0.15.0
    """

    __slots__ = ('cookie_name',)

    def __init__(  # noqa: WPS211
        self,
        *,
        cookie_name: str = DEFAULT_ACCESS_COOKIE,
        user_id_field: str = 'pk',
        algorithm: str = 'HS256',
        security_scheme_name: str = 'jwt',
        secret: str | None = None,
        token_cls: type[JWToken] = JWToken,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_expiry: bool = True,
        verify_issued_at: bool = True,
        verify_jwt_id: bool = True,
        verify_not_before: bool = True,
        verify_subject: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        Same as :class:`~dmr.security.jwt.auth.JWTAsyncAuth`,
        but *cookie_name* replaces ``auth_header`` and ``auth_scheme``,
        because cookies store the encoded token without any prefix.
        """
        super().__init__(
            user_id_field=user_id_field,
            algorithm=algorithm,
            security_scheme_name=security_scheme_name,
            secret=secret,
            token_cls=token_cls,
            leeway=leeway,
            accepted_audiences=accepted_audiences,
            accepted_issuers=accepted_issuers,
            require_claims=require_claims,
            verify_expiry=verify_expiry,
            verify_issued_at=verify_issued_at,
            verify_jwt_id=verify_jwt_id,
            verify_not_before=verify_not_before,
            verify_subject=verify_subject,
            strict_audience=strict_audience,
            enforce_minimum_key_length=enforce_minimum_key_length,
        )
        self.cookie_name = cookie_name

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Enforce CSRF, then authenticate via the cookie token."""
        self._ensure_csrf(controller)
        return await super().__call__(endpoint, controller)
