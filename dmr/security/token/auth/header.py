import datetime as dt
from typing import TYPE_CHECKING, Literal, Self, overload

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.security.token.models import Token
    from dmr.serializer import BaseSerializer


class _BaseTokenAuth:
    """Base class for DB-backed opaque token authentication.

    .. note::

        By default every successful authentication performs an extra
        ``UPDATE`` to persist ``last_used_at``.  Pass
        ``update_last_used=False`` to skip this write for high-traffic
        endpoints where tracking last-use is not required.
    """

    __slots__ = (
        'cookie_name',
        'header_name',
        'prefix',
        'query_param',
        'security_scheme_name',
        'update_last_used',
    )

    def __init__(
        self,
        *,
        header_name: str = 'X-API-Token',
        prefix: str = '',
        query_param: str = 'token',
        cookie_name: str = 'token',
        security_scheme_name: str = 'token',
        update_last_used: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        - *header_name* — which header carries the raw token (default
          ``X-API-Token``).  Use ``'Authorization'`` for RFC 7235-style
          bearer auth (see *prefix* below).
        - *prefix* — scheme prefix expected before the token in the header
          value (default ``''``, i.e. the header value is used verbatim).
          Set to ``'Token'`` or ``'Bearer'`` when *header_name* is
          ``'Authorization'`` — e.g. ``prefix='Token'`` requires the client
          to send ``Authorization: Token <raw-token>``.
        - *query_param* — which query string parameter carries the raw token
          (default ``token``).
        - *cookie_name* — which cookie carries the raw token (default
          ``token``).
        - *security_scheme_name* — name used in OpenAPI security scheme map.

        **Common configurations:**

        .. code-block:: python

            # Default — custom header, no prefix
            TokenSyncAuth()  # X-API-Token: <token>

            # DRF-compatible
            TokenSyncAuth(header_name='Authorization', prefix='Token')

            # Bearer style
            TokenSyncAuth(header_name='Authorization', prefix='Bearer')
        """
        self.header_name = header_name
        self.prefix = prefix
        self.query_param = query_param
        self.cookie_name = cookie_name
        self.security_scheme_name = security_scheme_name
        self.update_last_used = update_last_used

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self.header_name == 'Authorization':
            # RFC 7235 reserves the Authorization header for the `http` scheme.
            # Using `apiKey` + `name: Authorization` is invalid in OpenAPI 3.x.
            return {
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme='bearer',
                    description='Opaque token authentication',
                ),
            }
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header_name,
                security_scheme_in='header',
                description='Opaque token authentication',
            ),
        }

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """
        Extract the raw token string from the request.

        By default reads from the header specified by *header_name*, stripping
        any *prefix*.  Override this method to read from a different source
        (cookie, query string, request body, etc.).
        """
        header_value = request.headers.get(self.header_name)
        if header_value is None:
            return None
        if self.prefix:
            expected = f'{self.prefix} '
            if not header_value.startswith(expected):
                return None
            return header_value[len(expected) :]
        return header_value


def _token_model() -> 'type[Token]':
    """Deferred import so models are not loaded before app registry is ready."""
    from dmr.security.token.models import Token  # noqa: PLC0415

    return Token


def _set_request_attrs(
    request: HttpRequest,
    user: 'AbstractBaseUser',
    *,
    token: 'Token',
) -> None:
    """Set all required properties to the authed request."""
    request.user = user

    async def auser() -> 'AbstractBaseUser':  # noqa: WPS430
        return user

    request.auser = auser
    request.__dmr_token__ = token  # type: ignore[attr-defined]


class TokenSyncAuth(_BaseTokenAuth, SyncAuth):
    """Sync opaque token auth; reads from ``X-API-Token`` by default."""

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Authenticate via opaque token."""
        raw_token = self.get_raw_token(controller.request)
        if raw_token is None:
            return None
        self.authenticate(controller.request, raw_token)
        return self

    def authenticate(
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = self.get_token(raw_token)
        self.check_user(token.user)
        if self.update_last_used:
            self.mark_token_used(token)
        self.set_request_attrs(request, token.user, token=token)
        return token.user

    def get_token(self, raw_token: str) -> 'Token':
        """Look up and validate the token from the DB."""
        model = _token_model()
        token_hash = model.objects.hash_token(raw_token)
        try:
            token = model.objects.select_related('user').get(
                token_hash=token_hash,
            )
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
        if not token.is_active:
            raise NotAuthenticatedError
        return token

    def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    def mark_token_used(self, token: 'Token') -> None:
        """Persist token usage timestamp after successful authentication."""
        token.last_used_at = dt.datetime.now(dt.UTC)
        token.save(update_fields=['last_used_at', 'updated_at'])

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: 'Token',
    ) -> None:
        """Set current user as authed for this request."""
        _set_request_attrs(request, user, token=token)


class TokenAsyncAuth(_BaseTokenAuth, AsyncAuth):
    """Async opaque token auth; reads from ``X-API-Token`` by default."""

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Authenticate via opaque token."""
        raw_token = self.get_raw_token(controller.request)
        if raw_token is None:
            return None
        await self.authenticate(controller.request, raw_token)
        return self

    async def authenticate(
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = await self.get_token(raw_token)
        await self.check_user(token.user)
        if self.update_last_used:
            await self.mark_token_used(token)
        await self.set_request_attrs(request, token.user, token=token)
        return token.user

    async def get_token(self, raw_token: str) -> 'Token':
        """Look up and validate the token from the DB."""
        model = _token_model()
        token_hash = model.objects.hash_token(raw_token)
        try:
            token = await model.objects.select_related('user').aget(
                token_hash=token_hash,
            )
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
        if not token.is_active:
            raise NotAuthenticatedError
        return token

    async def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    async def mark_token_used(self, token: 'Token') -> None:
        """Persist token usage timestamp after successful authentication."""
        token.last_used_at = dt.datetime.now(dt.UTC)
        await token.asave(update_fields=['last_used_at', 'updated_at'])

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: 'Token',
    ) -> None:
        """Set current user as authed for this request."""
        _set_request_attrs(request, user, token=token)


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> 'Token': ...


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Token | None': ...


def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Token | None':
    """
    Return the Token from request, if it was authed with one.

    When *strict* is passed and *request* has no token,
    we raise :exc:`AttributeError`.
    """
    token = getattr(request, '__dmr_token__', None)
    if token is None and strict:
        raise AttributeError('__dmr_token__')
    return token
