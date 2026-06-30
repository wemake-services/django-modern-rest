from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, override

from django.contrib import admin
from django.db.models import Model
from django.db.models.query import QuerySet
from django.http import HttpRequest

from dmr.security.token.logic import token_is_active, token_revoke
from dmr.security.token.models import Token

_ModelT = TypeVar('_ModelT', bound=Model)

if TYPE_CHECKING:
    ModelAdmin = admin.ModelAdmin
else:

    class ModelAdmin(admin.ModelAdmin, Generic[_ModelT]): ...  # noqa: D101, WPS604


@admin.register(Token)
class TokenAdmin(ModelAdmin[Token]):
    """Admin configuration for opaque auth tokens.

    Tokens cannot be created from this admin. Issuing a token requires
    :func:`~dmr.security.token.logic.token_create`, which returns the
    raw token value exactly once. There is no way for an admin add-form
    to display that value back to whoever submitted it, so creation
    is disabled here by design, not by oversight.
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
        return token_is_active(token)

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
        for token in queryset:
            if token_is_active(token):
                token_revoke(token)
                revoked += 1
        self.message_user(request, f'Revoked {revoked} token(s).')
