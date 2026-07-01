import datetime as dt
from typing import TYPE_CHECKING, Self

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import SecurityRequirement
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.security.token.logic import token_hash, token_is_active

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.security.token.models import Token
    from dmr.serializer import BaseSerializer


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


class _BaseTokenAuth:  # pyright: ignore[reportUnusedClass]
    """Base class for DB-backed opaque token authentication.

    .. note::

        ``update_last_used`` is opt-in and defaults to ``False``.
        Pass ``update_last_used=True`` to persist ``last_used_at``
        on every successful authentication. This adds an extra
        ``UPDATE`` per request, so only enable it where last-use
        tracking is actually needed.
    """

    __slots__ = (
        'security_scheme_name',
        'update_last_used',
    )

    def __init__(
        self,
        *,
        security_scheme_name: str = 'token',
        update_last_used: bool = False,
    ) -> None:
        self.security_scheme_name = security_scheme_name
        self.update_last_used = update_last_used

    def token_model(self) -> 'type[Token]':
        """Returns the Token model. Override to use a custom model."""
        from dmr.security.token.models import Token  # noqa: PLC0415

        return Token

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}


class _BaseTokenSyncAuth(_BaseTokenAuth, SyncAuth):  # noqa: WPS214 # pyright: ignore[reportUnusedClass]
    """Shared sync authentication pipeline for single-source token auth."""

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

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Extract the raw token string from the request. Must be overridden."""
        raise NotImplementedError

    def authenticate(
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = self.get_token(raw_token)
        self.check_token(token)
        self.check_user(token.user)
        if self.update_last_used:
            self.mark_token_used(token)
        self.set_request_attrs(request, token.user, token=token)
        return token.user

    def get_token(self, raw_token: str) -> 'Token':
        """Look up and validate the token from the DB."""
        model = self.token_model()
        hashed_token = token_hash(raw_token)
        token = model.objects.select_related('user').filter(
            token_hash=hashed_token,
        ).first()
        if token is None:
            raise NotAuthenticatedError
        return token

    def check_token(self, token: 'Token') -> None:
        """Raise NotAuthenticatedError if the token is not active."""
        if not token_is_active(token):
            raise NotAuthenticatedError

    def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    def mark_token_used(self, token: 'Token') -> None:
        """Persist token usage timestamp after successful authentication."""
        now = dt.datetime.now(dt.UTC)
        self.token_model().objects.filter(pk=token.pk).update(
            last_used_at=now,
            updated_at=now,
        )
        token.last_used_at = now
        token.updated_at = now

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: 'Token',
    ) -> None:
        """Set current user as authed for this request."""
        _set_request_attrs(request, user, token=token)


class _BaseTokenAsyncAuth(_BaseTokenAuth, AsyncAuth):  # noqa: WPS214 # pyright: ignore[reportUnusedClass]
    """Shared async authentication pipeline for single-source token auth."""

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

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Extract the raw token string from the request. Must be overridden."""
        raise NotImplementedError

    async def authenticate(
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = await self.get_token(raw_token)
        await self.check_token(token)
        await self.check_user(token.user)
        if self.update_last_used:
            await self.mark_token_used(token)
        await self.set_request_attrs(request, token.user, token=token)
        return token.user

    async def get_token(self, raw_token: str) -> 'Token':
        """Look up and validate the token from the DB."""
        model = self.token_model()
        hashed_token = token_hash(raw_token)
        token = await model.objects.select_related('user').filter(
            token_hash=hashed_token,
        ).afirst()
        if token is None:
            raise NotAuthenticatedError
        return token

    async def check_token(self, token: 'Token') -> None:
        """Raise NotAuthenticatedError if the token is not active."""
        if not token_is_active(token):
            raise NotAuthenticatedError

    async def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    async def mark_token_used(self, token: 'Token') -> None:
        """Persist token usage timestamp after successful authentication."""
        now = dt.datetime.now(dt.UTC)
        await (
            self
            .token_model()
            .objects.filter(pk=token.pk)
            .aupdate(
                last_used_at=now,
                updated_at=now,
            )
        )
        token.last_used_at = now
        token.updated_at = now

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: 'Token',
    ) -> None:
        """Set current user as authed for this request."""
        _set_request_attrs(request, user, token=token)
