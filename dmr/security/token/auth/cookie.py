from typing import TYPE_CHECKING, Final, Self

from django.http import HttpRequest
from typing_extensions import override

from dmr.internal.csrf import CSRFAuthMixin
from dmr.openapi.objects import SecurityScheme
from dmr.security.csrf import CSRF_SCHEME_NAME
from dmr.security.token.auth.base import BaseTokenAsyncAuth, BaseTokenSyncAuth
from dmr.security.token.token import DEFAULT_TOKEN_ALGORITHM, DEFAULT_TOKEN_SALT

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

_DEFAULT_PARAM: Final = 'token'


class _BaseCookieTokenAuth(CSRFAuthMixin):
    """Reads opaque tokens from a request cookie."""

    # Slots are declared on the concrete classes below,
    # otherwise we get a layout conflict when mixing them in.
    __slots__ = ()

    cookie_name: str

    @override
    def auth_security_scheme(self) -> SecurityScheme:
        """Provides a security schema definition."""
        return SecurityScheme(
            type='apiKey',
            name=self.cookie_name,
            security_scheme_in='cookie',
            description='Opaque token authentication via cookie',
        )

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from a cookie."""
        return request.COOKIES.get(self.cookie_name)

    @override
    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        # We must check that token is actually present,
        # so otherwise, we can skip this auth and try the next one,
        # without triggering the CSRF error, see #1289
        if self.get_raw_token(controller.request):
            super()._ensure_csrf(controller)


class CookieTokenSyncAuth(_BaseCookieTokenAuth, BaseTokenSyncAuth):
    """
    Sync opaque token auth reading from a cookie.

    CSRF is automatically enforced before any other actions.

    .. versionadded:: 0.12.0
    .. versionchanged:: 0.16.0
        Fixed how CSRF schema is generated.

    """

    __slots__ = ('cookie_name', 'csrf_scheme_name')

    def __init__(  # noqa: WPS211
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        csrf_scheme_name: str = CSRF_SCHEME_NAME,
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
        self.csrf_scheme_name = csrf_scheme_name
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

    .. versionadded:: 0.12.0
    .. versionchanged:: 0.16.0
        Fixed how CSRF schema is generated.

    """

    __slots__ = ('cookie_name', 'csrf_scheme_name')

    def __init__(  # noqa: WPS211
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        csrf_scheme_name: str = CSRF_SCHEME_NAME,
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
        self.csrf_scheme_name = csrf_scheme_name
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
