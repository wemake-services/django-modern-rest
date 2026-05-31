from __future__ import annotations

from django.contrib import admin

from dmr.security.token.models import Token


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin configuration for opaque auth tokens."""

    list_display = (
        'id',
        'name',
        'user',
        'is_active',
        'last_used_at',
        'expires_at',
        'revoked_at',
        'created_at',
    )
    list_filter = (
        'created_at',
        'last_used_at',
        'expires_at',
        'revoked_at',
    )
    search_fields = ('name', 'user__username', 'user__email', 'token_hash')
    readonly_fields = ('token_hash', 'created_at', 'updated_at', 'last_used_at')
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
