import datetime as dt
import secrets
from typing import Final, Self, final

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from typing_extensions import Sentinel, override

from dmr.internal.model_fields import (
    CharField,
    DateTimeField,
    DateTimeFieldNullable,
    UserForeignKey,
)
from dmr.security.token import TokenLikeAsync, TokenLikeSync
from dmr.security.token.token import (
    RAW_TOKEN_SIZE,
    get_token_hash,
    resolve_expiry,
)
from dmr.types import EMPTY

_REVOKE_FIELDS: Final = ('revoked_at', 'updated_at')
_LAST_USED_FIELDS: Final = ('last_used_at', 'updated_at')


@final
class Token(TokenLikeSync, TokenLikeAsync, models.Model):  # noqa: WPS214
    """Model representing a DB-backed opaque auth token."""

    user: UserForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dmr_tokens',
    )
    name: CharField = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
    )
    token_hash: CharField = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Token hash'),
    )
    expires_at: DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires at'),
    )
    revoked_at: DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Revoked at'),
    )
    last_used_at: DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last used at'),
    )
    created_at: DateTimeField = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )
    updated_at: DateTimeField = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at'),
    )

    class Meta:
        abstract = 'dmr.security.token.app' not in settings.INSTALLED_APPS
        verbose_name = _('Token')
        verbose_name_plural = _('Tokens')

    @override
    def __str__(self) -> str:
        user_id = self.user_id  # type: ignore[attr-defined]
        return f'Token {self.name!r} for {user_id=}'

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
    def get_user(self) -> 'AbstractBaseUser':  # noqa: WPS615
        """Get user that this token belongs to."""
        return self.user

    @override
    async def aget_user(self) -> 'AbstractBaseUser':
        """Async get user that this token belongs to."""
        return self.user

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
    def revoke(
        self,
        *,
        at: dt.datetime | None = None,
    ) -> None:
        """Mark this token as revoked."""
        self._update_revoked(at)
        self.save(update_fields=_REVOKE_FIELDS)

    @override
    async def arevoke(
        self,
        *,
        at: dt.datetime | None = None,
    ) -> None:
        """Async mark this token as revoked."""
        self._update_revoked(at)
        await self.asave(update_fields=_REVOKE_FIELDS)

    @classmethod
    @override
    def issue(
        cls,
        *,
        user: 'AbstractBaseUser',
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> tuple[Self, str]:
        """Create a new token, returning the token model and raw token data."""
        raw_token = secrets.token_urlsafe(RAW_TOKEN_SIZE)
        token = cls.objects.create(
            user=user,
            name=name,
            token_hash=get_token_hash(raw_token),
            expires_at=resolve_expiry(expires_at),
        )
        return token, raw_token

    @classmethod
    @override
    async def aissue(
        cls,
        *,
        user: 'AbstractBaseUser',
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> 'tuple[Token, str]':
        """Async version of :meth:`Token.issue`."""
        raw_token = secrets.token_urlsafe(RAW_TOKEN_SIZE)
        token = await cls.objects.acreate(
            user=user,
            name=name,
            token_hash=get_token_hash(raw_token),
            expires_at=resolve_expiry(expires_at),
        )
        return token, raw_token

    @classmethod
    @override
    def find_raw(cls, raw_token: str) -> Self | None:
        """Find token by its hash."""
        return (
            cls.objects
            .select_related('user')
            .filter(token_hash=get_token_hash(raw_token))
            .first()
        )

    @classmethod
    @override
    async def afind_raw(cls, raw_token: str) -> Self | None:
        """Async find token by its hash."""
        return (
            await cls.objects
            .select_related('user')
            .filter(token_hash=get_token_hash(raw_token))
            .afirst()
        )

    def _update_used(self) -> None:
        now = dt.datetime.now(dt.UTC)
        self.last_used_at = now
        self.updated_at = now

    def _update_revoked(self, at: dt.datetime | None = None) -> None:
        self.revoked_at = at or dt.datetime.now(dt.UTC)
