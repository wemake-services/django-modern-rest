from typing import TYPE_CHECKING, Any, Final, Protocol

from dmr.exceptions import NotAuthenticatedError
from dmr.security.jwt.token import JWToken

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.security.jwt.blocklist.models import BlocklistedJWToken

#: Claim that the blocklist uses to identify tokens.
_JTI_CLAIM: Final = 'jti'


class _JWTAuth(Protocol):
    def blocklist_model(self) -> type['BlocklistedJWToken']: ...

    def token_jti(self, token: JWToken) -> str: ...


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
    # Provided by the auth class we are mixed into:
    require_claims: 'Sequence[str] | None'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Force the ``jti`` claim to be required.

        The blocklist stores tokens by their ``jti``,
        so a token without one can never be blocklisted.
        Accepting such tokens would mean that the blocklist
        is silently bypassed, we require the claim instead.
        
        .. versionadded:: 0.15.0
        """
        super().__init__(*args, **kwargs)
        require_claims = list(self.require_claims or ())
        if _JTI_CLAIM not in require_claims:
            require_claims.append(_JTI_CLAIM)
        self.require_claims = require_claims

    def blocklist_model(self) -> type['BlocklistedJWToken']:
        """Returns the model to be used."""
        from dmr.security.jwt.blocklist.models import (  # noqa: PLC0415
            BlocklistedJWToken,
        )

        return BlocklistedJWToken

    def token_jti(self, token: JWToken) -> str:
        """
        Return the ``jti`` this token is blocklisted by.

        Tokens decoded by this auth always have one, because ``jti``
        is required. But a hand-made token or a custom
        :class:`~dmr.security.jwt.token.JWToken` subclass can still
        reach us without it, and ``None`` would match no blocklist rows
        at all, while :meth:`blocklist` would fail on a database
        constraint. Both cases mean the same thing: this token cannot
        be used with the blocklist.

        Raises:
            NotAuthenticatedError: If the token has no ``jti``.

        .. versionadded:: 0.15.0
        """
        if token.jti is None:
            raise NotAuthenticatedError
        return token.jti


class JWTokenBlocklistSyncMixin(_BaseBlocklistMixin):
    """Sync mixin for working with tokens blocklist."""

    def check_auth(
        self: _JWTSyncAuth,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Check if the token is in the black list, if so raise the error."""
        super().check_auth(user, token)  # type: ignore[safe-super]
        jti = self.token_jti(token)
        if self.blocklist_model().objects.filter(jti=jti).exists():
            raise NotAuthenticatedError

    def blocklist(
        self: _JWTSyncAuth,
        token: JWToken,
    ) -> tuple['BlocklistedJWToken', bool]:
        """Add token to the blocklist."""
        return self.blocklist_model().objects.get_or_create(
            jti=self.token_jti(token),
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
        jti = self.token_jti(token)
        if await self.blocklist_model().objects.filter(jti=jti).aexists():
            raise NotAuthenticatedError

    async def blocklist(
        self: _JWTAsyncAuth,
        token: JWToken,
    ) -> tuple['BlocklistedJWToken', bool]:
        """Add token to the blocklist."""
        jti = self.token_jti(token)
        user = await self.get_user(token)
        return await self.blocklist_model().objects.aget_or_create(
            jti=jti,
            defaults={
                'user': user,
                'expires_at': token.exp,
            },
        )
