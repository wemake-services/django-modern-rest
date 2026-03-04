from typing import TYPE_CHECKING, Protocol

from dmr.exceptions import NotAuthenticatedError
from dmr.security.jwt.token import JWToken

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.security.jwt.blocklist.models import BlocklistedJWToken


class _JWTAuth(Protocol):
    def blocklist_model(self) -> type['BlocklistedJWToken']: ...


class _JWTSyncAuth(_JWTAuth, Protocol):
    def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None: ...

    def get_user(self, token: JWToken) -> 'AbstractBaseUser': ...


class _JWTAsyncAuth(_JWTAuth, Protocol):
    async def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None: ...

    async def get_user(self, token: JWToken) -> 'AbstractBaseUser': ...


class _BaseBlocklistMixin:
    def blocklist_model(self) -> type['BlocklistedJWToken']:
        """Returns the model to be used."""
        from dmr.security.jwt.blocklist.models import (  # noqa: PLC0415
            BlocklistedJWToken,
        )

        return BlocklistedJWToken


class JWTokenBlocklistSyncMixin(_BaseBlocklistMixin):
    """Sync mixin for working with tokens blocklist."""

    def check_auth(
        self: _JWTSyncAuth,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Check if the token is in the black list, if so raise the error."""
        super().check_auth(user, token)  # type: ignore[safe-super]
        if self.blocklist_model().objects.filter(jti=token.jti).exists():
            raise NotAuthenticatedError

    def blocklist(
        self: _JWTSyncAuth,
        token: JWToken,
    ) -> tuple['BlocklistedJWToken', bool]:
        """Add token to the blocklist."""
        return self.blocklist_model().objects.get_or_create(
            jti=token.jti,
            defaults={
                'user': self.get_user(token),
                'expires_at': token.exp,
            },
        )


class JWTokenBlocklistAsyncMixin(_BaseBlocklistMixin):
    """Async mixin for working with tokens blocklist."""

    async def check_auth(
        self: _JWTAsyncAuth,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Check if the token is in the black list, if so raise the error."""
        await super().check_auth(user, token)  # type: ignore[safe-super]
        if await self.blocklist_model().objects.filter(jti=token.jti).aexists():
            raise NotAuthenticatedError

    async def blocklist(
        self: _JWTAsyncAuth,
        token: JWToken,
    ) -> tuple['BlocklistedJWToken', bool]:
        """Add token to the blocklist."""
        user = await self.get_user(token)
        return await self.blocklist_model().objects.aget_or_create(
            jti=token.jti,
            defaults={
                'user': user,
                'expires_at': token.exp,
            },
        )
