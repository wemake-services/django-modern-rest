from __future__ import annotations

from django.contrib import admin
from django.db import transaction
from django.db.models.query import QuerySet
from django.http import HttpRequest
from typing_extensions import override

from dmr.internal.admin import ModelAdmin
from dmr.security.token.app.models import Token


@admin.register(Token)
class TokenAdmin(ModelAdmin[Token]):
    """Admin configuration for opaque auth tokens.

    Tokens cannot be created from this admin. Issuing a token requires
    :func:`~dmr.security.token.logic.token_create`, which returns the
    raw token value exactly once. There is no way for an admin add-form
    to display that value back to whoever submitted it, so creation
    is disabled here by design, not by oversight.

    .. versionadded:: 0.12.0
    """

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
    actions = ('revoke_selected',)

    @admin.display(boolean=True, description='Is active')
    def display_is_active(self, token: Token) -> bool:
        """Display token active state in admin list."""
        return token.is_active

    @override
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Tokens must be issued via ``token_create``, not this admin."""
        return False

    @admin.action(description='Revoke selected tokens')
    def revoke_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[Token],
    ) -> None:
        """Revoke all active tokens in the selected queryset."""
        revoked = 0
        with transaction.atomic():
            for token in queryset.select_for_update():
                token.revoke()
                revoked += 1
        self.message_user(request, f'Revoked {revoked} token(s).')
