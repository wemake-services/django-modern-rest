import datetime as dt
import secrets
from typing import ClassVar, TypeAlias, cast

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.expressions import Combinable
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext_lazy as _
from typing_extensions import Sentinel, override

from dmr.settings import Settings, resolve_setting
from dmr.types import EMPTY

_BaseFkData: TypeAlias = int | str | Combinable
_ForeignKey: TypeAlias = (
    'models.ForeignKey[_BaseFkData | AbstractBaseUser, AbstractBaseUser]'
)
_CharField: TypeAlias = 'models.CharField[_BaseFkData, str]'
_DateTimeField: TypeAlias = (
    'models.DateTimeField[str | dt.datetime | Combinable, dt.datetime]'
)
_DateTimeFieldNullable: TypeAlias = 'models.DateTimeField[str | dt.datetime | Combinable | None, dt.datetime | None]'  # noqa: E501


class TokenManager(models.Manager['Token']):
    """
    Manager for the Token model.

    .. warning::

        Token hashes are derived from ``SECRET_KEY`` via HMAC-SHA256.
        Rotating ``SECRET_KEY`` silently invalidates **all** existing tokens
        because the stored hashes will no longer match any incoming raw token.
    """

    def hash_token(self, raw_token: str) -> str:
        """Return HMAC-SHA256 hex digest of raw_token."""
        return salted_hmac(
            'dmr.security.token',
            raw_token,
            secret=settings.SECRET_KEY,
            algorithm='sha256',
        ).hexdigest()

    def get_expires_at(
        self,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> dt.datetime | None:
        """Resolve the expiry datetime, falling back to the global default."""
        if expires_at is EMPTY:
            default_expiry: dt.timedelta | None = resolve_setting(
                Settings.token_default_expiry,
            )
            if default_expiry is None:
                return None
            return dt.datetime.now(dt.UTC) + default_expiry
        return cast(dt.datetime | None, expires_at)

    def create_token(
        self,
        *,
        user: AbstractBaseUser,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> 'tuple[Token, str]':
        """
        Create a new token, returning ``(Token instance, raw token string)``.

        If *expires_at* is not provided the token expires after
        ``DMR_SETTINGS[Settings.token_default_expiry]``.
        Pass ``None`` explicitly to create a non-expiring token.
        """
        raw_token = secrets.token_urlsafe(32)
        token = self.create(
            user=user,
            name=name,
            token_hash=self.hash_token(raw_token),
            expires_at=self.get_expires_at(expires_at),
        )
        return token, raw_token

    async def acreate_token(
        self,
        *,
        user: AbstractBaseUser,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> 'tuple[Token, str]':
        """
        Async version of :meth:`create_token`.

        If *expires_at* is not provided the token expires after
        ``DMR_SETTINGS[Settings.token_default_expiry]``.
        Pass ``None`` explicitly to create a non-expiring token.
        """
        raw_token = secrets.token_urlsafe(32)
        token = await self.acreate(
            user=user,
            name=name,
            token_hash=self.hash_token(raw_token),
            expires_at=self.get_expires_at(expires_at),
        )
        return token, raw_token


class Token(models.Model):
    """Model representing a DB-backed opaque auth token."""

    user: _ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dmr_tokens',
    )
    name: _CharField = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
    )
    token_hash: _CharField = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Token hash'),
    )
    expires_at: _DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires at'),
    )
    revoked_at: _DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Revoked at'),
    )
    last_used_at: _DateTimeFieldNullable = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last used at'),
    )
    created_at: _DateTimeField = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )
    updated_at: _DateTimeField = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at'),
    )

    objects: ClassVar[TokenManager] = TokenManager()  # noqa: WPS110  # pyright: ignore[reportIncompatibleVariableOverride]

    class Meta:
        abstract = 'dmr.security.token' not in settings.INSTALLED_APPS
        verbose_name = _('Token')
        verbose_name_plural = _('Tokens')

    @override
    def __str__(self) -> str:
        return f'Token "{self.name}" for {self.user}'

    @property
    def is_expired(self) -> bool:
        """Return True if the token has passed its expiry date."""
        if self.expires_at is None:
            return False
        return dt.datetime.now(dt.UTC) >= self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Return True if the token has been revoked."""
        return self.revoked_at is not None

    @property
    def is_active(self) -> bool:
        """Return True if the token is neither expired nor revoked."""
        return not self.is_expired and not self.is_revoked

    def revoke(self, *, at: dt.datetime | None = None) -> None:
        """Mark this token as revoked."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)
        self.save(update_fields=['revoked_at', 'updated_at'])

    async def arevoke(self, *, at: dt.datetime | None = None) -> None:
        """Async version of :meth:`revoke`."""
        self.revoked_at = at or dt.datetime.now(dt.UTC)
        await self.asave(update_fields=['revoked_at', 'updated_at'])
