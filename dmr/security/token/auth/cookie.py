from typing import Final

from django.http import HttpRequest
from typing_extensions import override

from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.token.auth.header import TokenAsyncAuth, TokenSyncAuth

_DEFAULT_PARAM: Final = 'token'


class CookieTokenSyncAuth(TokenSyncAuth):
    """
    Sync opaque token auth reading from a cookie.

    .. warning::
        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts.  Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            cookie_name=cookie_name,
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )

    @property
    @override
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
    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from a cookie."""
        return request.COOKIES.get(self.cookie_name)


class CookieTokenAsyncAuth(TokenAsyncAuth):
    """
    Async opaque token auth reading from a cookie.

    .. warning::
        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts.  Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            cookie_name=cookie_name,
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )

    @property
    @override
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
    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from a cookie."""
        return request.COOKIES.get(self.cookie_name)
