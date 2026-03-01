from datetime import date
from typing import TypeAlias

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.expressions import Combinable
from typing_extensions import override

from dmr.security.blocklist.apps import BlocklistConfig

_ForeignKey: TypeAlias = (
    'models.ForeignKey[str | AbstractBaseUser | Combinable, AbstractBaseUser ]'
)
_CharField: TypeAlias = 'models.CharField[str | int | Combinable, str]'
_DateTimeField: TypeAlias = (
    'models.DateTimeField[str | date | Combinable, date]'
)


class BlocklistedJWTToken(models.Model):
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
        abstract = BlocklistConfig.name not in settings.INSTALLED_APPS

    @override
    def __str__(self) -> str:
        return f'Token for {self.user} {self.jti}'
