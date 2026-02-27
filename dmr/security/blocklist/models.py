from typing import Any, override

from django.conf import settings
from django.db import models

from dmr.security.blocklist.apps import BlocklistConfig


class BlocklistedJWTToken(models.Model):
    """Model for Blocklisted token."""

    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    jti: models.CharField[Any, Any] = models.CharField(
        unique=True,
        max_length=255,
    )
    expires_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at: models.DateTimeField[Any, Any] = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = BlocklistConfig.name not in settings.INSTALLED_APPS

    @override
    def __str__(self) -> str:
        return f'Token for {self.user} {self.jti}'
