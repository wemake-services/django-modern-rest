import datetime as dt
import secrets
from typing import Final, Self, final

from django.db import models
from typing_extensions import Sentinel, override

from dmr.security.token.token import (
    TokenLikeAsync,
    TokenLikeSync,
    get_token_hash,
    resolve_expiry,
)
from dmr.types import EMPTY
from server.apps.token_custom_user.models.user import ApiUser

_TOKEN_HASH_SIZE: Final = 64
_REVOKE_FIELDS: Final = ('revoked_at', 'updated_at')
_LAST_USED_FIELDS: Final = ('last_used_at', 'updated_at')


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Interfaces implementation

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
        self._update_used()
        self.save(update_fields=_LAST_USED_FIELDS)

    @override
    async def amark_used(self) -> None:
        """Async mark this token as used."""
        self._update_used()
        await self.asave(update_fields=_LAST_USED_FIELDS)

    @override
    def revoke(self, *, at: dt.datetime | None = None) -> None:
        """Mark this token as revoked."""
        self._update_revoked(at)
        self.save(update_fields=_REVOKE_FIELDS)

    @override
    async def arevoke(self, *, at: dt.datetime | None = None) -> None:
        """Async mark this token as revoked."""
        self._update_revoked(at)
        await self.asave(update_fields=_REVOKE_FIELDS)

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
        token, raw_token = cls._build(
            user=user,
            expires_at=expires_at,
            token_size=token_size,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        token.save()
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
        token, raw_token = cls._build(
            user=user,
            expires_at=expires_at,
            token_size=token_size,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        await token.asave()
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
        return cls._find(
            raw_token,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        ).first()

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
        return await cls._find(
            raw_token,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        ).afirst()

    def _update_used(self) -> None:
        """Refresh the last used timestamp, ``updated_at`` is automatic."""
        self.last_used_at = dt.datetime.now(dt.UTC)

    def _update_revoked(self, at: dt.datetime | None) -> None:
        """Refresh the revocation timestamp, ``updated_at`` is automatic."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)

    @classmethod
    def _build(  # noqa: WPS211
        cls,
        *,
        user: ApiUser,
        expires_at: dt.datetime | Sentinel | None,
        token_size: int | None,
        token_secret: str | None,
        token_salt: str | None,
        token_algorithm: str | None,
    ) -> tuple[Self, str]:
        """Build an unsaved token, shared by `issue` and `aissue`."""
        raw_token = secrets.token_urlsafe(token_size)
        token = cls(
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
    def _find(
        cls,
        raw_token: str,
        *,
        token_secret: str | None,
        token_salt: str | None,
        token_algorithm: str | None,
    ) -> models.QuerySet[Self]:
        """Query by token hash, shared by `find_raw` and `afind_raw`."""
        token_hash = get_token_hash(
            raw_token,
            secret=token_secret,
            salt=token_salt,
            algorithm=token_algorithm,
        )
        return cls.objects.select_related('owner').filter(token_hash=token_hash)
