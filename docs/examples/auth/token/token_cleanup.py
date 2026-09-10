import datetime as dt
from typing import Any, final

from django.core.management.base import BaseCommand
from django.db import models
from typing_extensions import override

from dmr.security.token.app.models import Token

#: How long dead tokens are kept around for auditing.
GRACE_PERIOD = dt.timedelta(days=30)


@final
class Command(BaseCommand):
    """Delete tokens that cannot authenticate anyone anymore."""

    help = 'Delete expired and revoked tokens.'

    @override
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: WPS110
        """Tokens with `expires_at=None` never expire, `__lt` skips them."""
        cutoff = dt.datetime.now(dt.UTC) - GRACE_PERIOD
        deleted, _ = Token.objects.filter(
            models.Q(expires_at__lt=cutoff) | models.Q(revoked_at__lt=cutoff),
        ).delete()
        self.stdout.write(f'Removed {deleted} tokens')
