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


class BlocklistedJWToken(models.Model):
    """Model for Blocklisted token."""

    user: _ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    jti: _CharField = models.CharField(
        unique=True,
        max_length=255,
    )
    expires_at: _DateTimeField = models.DateTimeField()
    created_at: _DateTimeField = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at: _DateTimeField = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = 'dmr.security.jwt.blocklist' not in settings.INSTALLED_APPS
        verbose_name = _('BlocklistedJWToken')
        verbose_name_plural = _('BlocklistedJWTokens')

    @override
    def __str__(self) -> str:
        return f'Blocked JWT token for {self.user} {self.jti}'
