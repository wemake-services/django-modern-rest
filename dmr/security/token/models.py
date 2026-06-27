import datetime as dt
from typing import TypeAlias

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.expressions import Combinable
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

_BaseFkData: TypeAlias = int | str | Combinable
_ForeignKey: TypeAlias = (
    'models.ForeignKey[_BaseFkData | AbstractBaseUser, AbstractBaseUser]'
)
_CharField: TypeAlias = 'models.CharField[_BaseFkData, str]'
_DateTimeField: TypeAlias = (
    'models.DateTimeField[str | dt.datetime | Combinable, dt.datetime]'
)
_DateTimeFieldNullable: TypeAlias = 'models.DateTimeField[str | dt.datetime | Combinable | None, dt.datetime | None]'  # noqa: E501


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

    class Meta:
        abstract = 'dmr.security.token' not in settings.INSTALLED_APPS
        verbose_name = _('Token')
        verbose_name_plural = _('Tokens')

    @override
    def __str__(self) -> str:
        return f'Token "{self.name}" for {self.user}'
