from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, Self

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.internal.csrf import ensure_csrf
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.token.auth.base import BaseTokenAsyncAuth, BaseTokenSyncAuth
from dmr.security.token.token import DEFAULT_TOKEN_ALGORITHM, DEFAULT_TOKEN_SALT

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

_DEFAULT_PARAM: Final = 'token'


class _BaseCookieTokenAuth(ResponseSpecProvider):
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
                description='Opaque token authentication via cookie',
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

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from a cookie."""
        return request.COOKIES.get(self.cookie_name)

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        ensure_csrf(controller)


class CookieTokenSyncAuth(_BaseCookieTokenAuth, BaseTokenSyncAuth):
    """
    Sync opaque token auth reading from a cookie.

    CSRF is automatically enforced before any other actions.

    .. warning::

        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts. Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.

    .. versionadded:: 0.12.0
    """

    __slots__ = ('cookie_name',)

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = False,
        token_secret: str | None = None,
        token_salt: str = DEFAULT_TOKEN_SALT,
        token_algorithm: str = DEFAULT_TOKEN_ALGORITHM,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        self.cookie_name = cookie_name

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Enforce CSRF, then authenticate via cookie token."""
        self._ensure_csrf(controller)
        return super().__call__(endpoint, controller)


class CookieTokenAsyncAuth(_BaseCookieTokenAuth, BaseTokenAsyncAuth):
    """
    Async opaque token auth reading from a cookie.

    CSRF is automatically enforced before any other actions.

    .. warning::

        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts. Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.

    .. versionadded:: 0.12.0
    """

    __slots__ = ('cookie_name',)

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = False,
        token_secret: str | None = None,
        token_salt: str = DEFAULT_TOKEN_SALT,
        token_algorithm: str = DEFAULT_TOKEN_ALGORITHM,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        self.cookie_name = cookie_name

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Enforce CSRF, then authenticate via cookie token."""
        self._ensure_csrf(controller)
        return await super().__call__(endpoint, controller)
