from django.contrib import admin

from dmr.security.jwt.blocklist.models import BlocklistedJWToken


@admin.register(BlocklistedJWToken)
class BlocklistedJWTokenAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin configuration for blocklisted JWT tokens."""

    list_display = (
        'id',
        'user',
        'jti',
        'expires_at',
        'created_at',
    )
    list_filter = (
        'created_at',
        'expires_at',
        'user',
    )
    search_fields = ('jti', 'user__username', 'user__email')
    readonly_fields = ('jti', 'created_at', 'updated_at', 'expires_at')
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
