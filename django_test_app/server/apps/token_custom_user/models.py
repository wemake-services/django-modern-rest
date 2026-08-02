import datetime as dt
import secrets
from typing import Final, Self, final

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from typing_extensions import Sentinel, override

from dmr.security.token.token import (
    TokenLikeAsync,
    TokenLikeSync,
    get_token_hash,
    resolve_expiry,
)
from dmr.types import EMPTY

_TOKEN_HASH_SIZE: Final = 64
_USERNAME_SIZE: Final = 150


@final
class ApiUser(AbstractBaseUser):
    """Custom user model, it is not ``settings.AUTH_USER_MODEL``."""

    username = models.CharField(max_length=_USERNAME_SIZE, unique=True)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'username'  # noqa: WPS115


@final
class ApiToken(  # noqa: WPS214
    TokenLikeSync[ApiUser],
    TokenLikeAsync[ApiUser],
    models.Model,
):
    """Custom token model with both sync and async interfaces."""

    owner = models.ForeignKey(
        ApiUser,
        on_delete=models.CASCADE,
        related_name='api_tokens',
    )
    token_hash = models.CharField(max_length=_TOKEN_HASH_SIZE, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    @property
    @override
    def is_expired(self) -> bool:
        """Return True if the token has passed its expiry date."""
        if self.expires_at is None:
            return False
        return dt.datetime.now(dt.UTC) >= self.expires_at

    @property
    @override
    def is_active(self) -> bool:
        """Return True if the token is neither expired nor revoked."""
        return not self.is_expired and self.revoked_at is None

    @override
    def get_user(self) -> ApiUser:
        """Get user that this token belongs to."""
        return self.owner

    @override
    async def aget_user(self) -> ApiUser:
        """Async get user that this token belongs to."""
        return self.owner

    @override
    def mark_used(self) -> None:
        """Mark this token as used."""
        self.last_used_at = dt.datetime.now(dt.UTC)
        self.save(update_fields=['last_used_at'])

    @override
    async def amark_used(self) -> None:
        """Async mark this token as used."""
        self.last_used_at = dt.datetime.now(dt.UTC)
        await self.asave(update_fields=['last_used_at'])

    @override
    def revoke(self, *, at: dt.datetime | None = None) -> None:
        """Mark this token as revoked."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)
        self.save(update_fields=['revoked_at'])

    @override
    async def arevoke(self, *, at: dt.datetime | None = None) -> None:
        """Async mark this token as revoked."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)
        await self.asave(update_fields=['revoked_at'])

    @classmethod
    @override
    def issue(  # noqa: WPS211
        cls,
        *,
        user: ApiUser,
        name: str,  # unused
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> tuple[Self, str]:
        """Create a new token, returning the token model and raw token data."""
        raw_token = secrets.token_urlsafe(token_size)
        token = cls.objects.create(
            owner=user,
            token_hash=get_token_hash(
                raw_token,
                secret=token_secret,
                salt=token_salt,
                algorithm=token_algorithm,
            ),
            expires_at=resolve_expiry(expires_at),
        )
        return token, raw_token

    @classmethod
    @override
    async def aissue(  # noqa: WPS211
        cls,
        *,
        user: ApiUser,
        name: str,  # unused
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> tuple[Self, str]:
        """Async version of :meth:`ApiToken.issue`."""
        raw_token = secrets.token_urlsafe(token_size)
        token = await cls.objects.acreate(
            owner=user,
            token_hash=get_token_hash(
                raw_token,
                secret=token_secret,
                salt=token_salt,
                algorithm=token_algorithm,
            ),
            expires_at=resolve_expiry(expires_at),
        )
        return token, raw_token

    @classmethod
    @override
    def find_raw(
        cls,
        raw_token: str,
        *,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> Self | None:
        """Find token by its hash."""
        token_hash = get_token_hash(
            raw_token,
            secret=token_secret,
            salt=token_salt,
            algorithm=token_algorithm,
        )
        return (
            cls.objects
            .select_related('owner')
            .filter(token_hash=token_hash)
            .first()
        )

    @classmethod
    @override
    async def afind_raw(
        cls,
        raw_token: str,
        *,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> Self | None:
        """Async find token by its hash."""
        token_hash = get_token_hash(
            raw_token,
            secret=token_secret,
            salt=token_salt,
            algorithm=token_algorithm,
        )
        return (
            await cls.objects
            .select_related('owner')
            .filter(token_hash=token_hash)
            .afirst()
        )
