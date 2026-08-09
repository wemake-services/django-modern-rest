from django.contrib import admin

from dmr.security.jwt.blocklist.admin import BlocklistedJWTokenAdmin
from dmr.security.jwt.blocklist.models import BlocklistedJWToken


def test_admin_registered() -> None:
    """Ensure that BlocklistedJWToken is registered in admin."""
    registered_admin = admin.site._registry.get(BlocklistedJWToken)
    assert isinstance(registered_admin, BlocklistedJWTokenAdmin)
