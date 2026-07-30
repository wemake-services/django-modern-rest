from typing import final

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from dmr.internal.model_fields import CharField, DateTimeField, UserForeignKey


@final
class BlocklistedJWToken(models.Model):
    """Model for Blocklisted token."""

    # TODO: add `verbose_name` to all the fields:
    user: UserForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    jti: CharField = models.CharField(
        unique=True,
        max_length=255,
    )
    expires_at: DateTimeField = models.DateTimeField()
    created_at: DateTimeField = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at: DateTimeField = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = 'dmr.security.jwt.blocklist' not in settings.INSTALLED_APPS
        verbose_name = _('BlocklistedJWToken')
        verbose_name_plural = _('BlocklistedJWTokens')

    @override
    def __str__(self) -> str:
        return f'Blocked JWT token for {self.user} {self.jti}'
