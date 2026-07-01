from __future__ import annotations

from typing import Any, cast
from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory

from dmr.security.token.admin import TokenAdmin
from dmr.security.token.logic import token_create, token_is_active
from dmr.security.token.models import Token


@pytest.mark.django_db
def test_token_admin_is_registered() -> None:
    """Test token admin is registered with Django admin site."""
    assert isinstance(admin.site._registry[Token], TokenAdmin)


@pytest.mark.django_db
def test_token_admin_has_no_add_permission(admin_user: User) -> None:
    """Test tokens cannot be added from the admin."""
    token_admin = TokenAdmin(Token, admin.site)
    request = RequestFactory().get('/admin/')

    assert not token_admin.has_add_permission(request)


@pytest.mark.django_db
def test_token_admin_display_is_active(admin_user: User) -> None:
    """Test the admin active-state column mirrors token state."""
    token, _ = token_create(user=admin_user, name='active-token')
    token_admin = TokenAdmin(Token, admin.site)

    assert token_admin.display_is_active(token)

    token.revoked_at = token.created_at
    token.save(update_fields=['revoked_at', 'updated_at'])

    assert not token_admin.display_is_active(token)
    assert not token_is_active(token)


@pytest.mark.django_db
def test_token_admin_revoke_selected(admin_user: User) -> None:
    """Test the admin bulk action revokes only active tokens."""
    active_token, _ = token_create(user=admin_user, name='active-token')
    revoked_token, _ = token_create(user=admin_user, name='revoked-token')
    revoked_token.revoked_at = revoked_token.created_at
    revoked_token.save(update_fields=['revoked_at', 'updated_at'])

    token_admin = TokenAdmin(Token, admin.site)
    message_user = Mock()
    cast(Any, token_admin).message_user = message_user
    request = RequestFactory().post('/admin/')

    token_admin.revoke_selected(
        request,
        Token.objects.filter(pk__in=[active_token.pk, revoked_token.pk]),
    )

    active_token.refresh_from_db()
    revoked_token.refresh_from_db()

    assert active_token.revoked_at is not None
    assert not token_is_active(active_token)
    assert not token_is_active(revoked_token)
    message_user.assert_called_once_with(
        request,
        'Revoked 1 token(s).',
    )
