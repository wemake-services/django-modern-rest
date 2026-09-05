import datetime as dt
from typing import Any, final

from django.core.management.base import BaseCommand
from typing_extensions import override

from dmr.security.jwt.blocklist.models import BlocklistedJWToken

#: Must be bigger than the `leeway` of all your jwt auth classes.
GRACE_PERIOD = dt.timedelta(days=1)


@final
class Command(BaseCommand):
    """Delete blocklist entries of tokens that are already expired."""

    help = 'Delete blocklist entries of tokens that are already expired.'

    @override
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: WPS110
        """Expired tokens are rejected by `exp` before the blocklist runs."""
        deleted, _ = BlocklistedJWToken.objects.filter(
            expires_at__lt=dt.datetime.now(dt.UTC) - GRACE_PERIOD,
        ).delete()
        self.stdout.write(f'Removed {deleted} blocklisted tokens')
