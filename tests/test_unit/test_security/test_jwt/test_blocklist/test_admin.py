import pytest
from django.contrib import admin

from dmr.security.jwt.blocklist.admin import BlocklistedJWTokenAdmin
from dmr.security.jwt.blocklist.models import BlocklistedJWToken


@pytest.fixture
def admin_instance() -> BlocklistedJWTokenAdmin:
    """Create admin instance for tests."""
    return BlocklistedJWTokenAdmin(BlocklistedJWToken, admin.site)


def test_admin_registered() -> None:
    """Ensure that BlocklistedJWToken is registered in admin."""
    registered_admin = admin.site._registry.get(BlocklistedJWToken)
    assert registered_admin is not None
    assert isinstance(registered_admin, BlocklistedJWTokenAdmin)


def test_list_display(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test list_display configuration."""
    assert admin_instance.list_display == (
        'id',
        'user',
        'jti',
        'expires_at',
        'created_at',
    )


def test_list_filter(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test list_filter configuration."""
    assert admin_instance.list_filter == (
        'created_at',
        'expires_at',
        'user',
    )


def test_search_fields(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test search_fields configuration."""
    assert admin_instance.search_fields == (
        'jti',
        'user__username',
        'user__email',
    )


def test_readonly_fields(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test readonly_fields configuration."""
    assert admin_instance.readonly_fields == (
        'jti',
        'created_at',
        'updated_at',
        'expires_at',
    )


def test_autocomplete_fields(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test autocomplete_fields configuration."""
    assert admin_instance.autocomplete_fields == ('user',)


def test_ordering(admin_instance: BlocklistedJWTokenAdmin) -> None:
    """Test ordering configuration."""
    assert admin_instance.ordering == ('-created_at',)
