from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from django.contrib import admin
from django.db.models import Model

from dmr.security.token.logic import token_is_active
from dmr.security.token.models import Token

_ModelT = TypeVar('_ModelT', bound=Model)

if TYPE_CHECKING:
    ModelAdmin = admin.ModelAdmin
else:

    class ModelAdmin(admin.ModelAdmin, Generic[_ModelT]): ...  # noqa: D101, WPS604


@admin.register(Token)
class TokenAdmin(ModelAdmin[Token]):
    """Admin configuration for opaque auth tokens."""

    list_display = (
        'id',
        'name',
        'user',
        'display_is_active',
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
    list_select_related = ('user',)
    search_fields = ('name', 'user__username', 'user__email', 'token_hash')
    readonly_fields = ('token_hash', 'created_at', 'updated_at', 'last_used_at')
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)

    @admin.display(boolean=True, description='Is active')
    def display_is_active(self, token: Token) -> bool:
        """Display token active state in admin list."""
        return token_is_active(token)
