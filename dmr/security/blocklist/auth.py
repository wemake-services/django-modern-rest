from typing import TYPE_CHECKING, ClassVar, Protocol

from dmr.exceptions import NotAuthenticatedError
from dmr.security.blocklist.models import BlocklistedJWTToken
from dmr.security.jwt.token import JWTToken

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


class _JWTAuth(Protocol):
    blocklist_model: ClassVar[type[BlocklistedJWTToken]]


class _JWTSyncAuth(_JWTAuth, Protocol):
    def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWTToken,
    ) -> None: ...

    def get_user(self, token: JWTToken) -> 'AbstractBaseUser': ...


class _JWTAsyncAuth(_JWTAuth, Protocol):
    async def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWTToken,
    ) -> None: ...

    async def get_user(self, token: JWTToken) -> 'AbstractBaseUser': ...


class JWTTokenBlocklistSyncMixin:
    """Sync mixin for working with tokens blocklist."""

    blocklist_model: ClassVar[type[BlocklistedJWTToken]] = BlocklistedJWTToken

    def check_auth(
        self: _JWTSyncAuth,
        user: 'AbstractBaseUser',
        token: JWTToken,
    ) -> None:
        """Check if the token is in the black list, if so raise the error."""
        super().check_auth(user, token)  # type: ignore[safe-super]
        if self.blocklist_model.objects.filter(jti=token.jti).exists():
            raise NotAuthenticatedError

    def blocklist(
        self: _JWTSyncAuth,
        token: JWTToken,
    ) -> tuple[BlocklistedJWTToken, bool]:
        """Add token to the blocklist."""
        jti = token.jti
        exp = token.exp
        user = self.get_user(token)

        return self.blocklist_model.objects.get_or_create(
            user=user,
            jti=jti,
            expires_at=exp,
        )


class JWTTokenBlocklistAsyncMixin:
    """Async mixin for working with tokens blocklist."""

    blocklist_model: ClassVar[type[BlocklistedJWTToken]] = BlocklistedJWTToken

    async def check_auth(
        self: _JWTAsyncAuth,
        user: 'AbstractBaseUser',
        token: JWTToken,
    ) -> None:
        """Check if the token is in the black list, if so raise the error."""
        await super().check_auth(user, token)  # type: ignore[safe-super]
        if await self.blocklist_model.objects.filter(jti=token.jti).aexists():
            raise NotAuthenticatedError

    async def blocklist(
        self: _JWTAsyncAuth,
        token: JWTToken,
    ) -> tuple[BlocklistedJWTToken, bool]:
        """Add token to the blocklist."""
        jti = token.jti
        exp = token.exp
        user = await self.get_user(token)

        return await self.blocklist_model.objects.aget_or_create(
            user=user,
            jti=jti,
            expires_at=exp,
        )
