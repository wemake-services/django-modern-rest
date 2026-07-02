from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security._csrf import (
    ensure_csrf,  # noqa: WPS450  # pyright: ignore[reportPrivateUsage]
)
from dmr.security.token.auth.base import (
    _BaseTokenAsyncAuth,  # noqa: WPS450  # pyright: ignore[reportPrivateUsage]
    _BaseTokenSyncAuth,  # noqa: WPS450  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

_DEFAULT_PARAM: Final = 'token'


class CookieTokenSyncAuth(_BaseTokenSyncAuth, ResponseSpecProvider):
    """
    Sync opaque token auth reading from a cookie.

    CSRF is enforced automatically after a successful token look-up.

    .. warning::
        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts.  Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.
    """

    __slots__ = ('cookie_name',)

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )
        self.cookie_name = cookie_name

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> 'CookieTokenSyncAuth | None':
        """Authenticate via cookie token, then enforce CSRF."""
        auth = super().__call__(endpoint, controller)
        if auth is None:
            return None
        ensure_csrf(controller)
        return auth

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


class CookieTokenAsyncAuth(_BaseTokenAsyncAuth, ResponseSpecProvider):
    """
    Async opaque token auth reading from a cookie.

    CSRF is enforced automatically after a successful token look-up.

    .. warning::
        Cookie-based authentication is vulnerable to CSRF attacks in
        browser-facing contexts.  Ensure that
        ``django.middleware.csrf.CsrfViewMiddleware`` is active whenever
        this auth class is used in a browser-facing application.
    """

    __slots__ = ('cookie_name',)

    def __init__(
        self,
        *,
        cookie_name: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )
        self.cookie_name = cookie_name

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> 'CookieTokenAsyncAuth | None':
        """Authenticate via cookie token, then enforce CSRF."""
        auth = await super().__call__(endpoint, controller)
        if auth is None:
            return None
        ensure_csrf(controller)
        return auth

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
