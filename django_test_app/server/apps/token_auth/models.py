import datetime as dt
import secrets
from typing import Final, Self, final

from django.contrib.auth.models import User
from django.db import models
from typing_extensions import Sentinel, override

from dmr.security.token.auth.base import TokenLikeSync
from dmr.security.token.token import (
    RAW_TOKEN_SIZE,
    get_token_hash,
    resolve_expiry,
)
from dmr.types import EMPTY

_SALTED_TOKEN_SIZE: Final = 64


@final
class CustomToken(TokenLikeSync[User], models.Model):
    """Custom model representing a DB-backed opaque auth token."""

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_tokens',
    )
    token_hash = models.CharField(max_length=_SALTED_TOKEN_SIZE, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    def get_user(self) -> User:
        """Get user that this token belongs to."""
        return self.owner

    @override
    def mark_used(self) -> None:
        """Mark this token as used."""
        # Not supported in this example, does nothing

    @override
    def revoke(
        self,
        *,
        at: dt.datetime | None = None,
    ) -> None:
        """Mark this token as revoked."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)
        self.save(update_fields=['revoked_at'])

    @classmethod
    @override
    def issue(
        cls,
        *,
        user: User,
        name: str,  # unused
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> tuple[Self, str]:
        """Create a new token, returning the token model and raw token data."""
        raw_token = secrets.token_urlsafe(RAW_TOKEN_SIZE)
        token = CustomToken.objects.create(
            owner=user,
            token_hash=get_token_hash(raw_token),
            expires_at=resolve_expiry(expires_at),
        )
        return token, raw_token

    @classmethod
    @override
    def find_raw(cls, raw_token: str) -> Self | None:
        """Find token by its hash."""
        return (
            CustomToken.objects
            .select_related('owner')
            .filter(token_hash=get_token_hash(raw_token))
            .first()
        )
