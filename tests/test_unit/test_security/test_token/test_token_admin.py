from __future__ import annotations

import datetime as dt
from typing import Any, cast
from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory

from dmr.security.token.app.admin import TokenAdmin
from dmr.security.token.app.models import Token


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
    token, _ = Token.issue(user=admin_user, name='active-token')
    token_admin = TokenAdmin(Token, admin.site)

    assert token_admin.display_is_active(token)

    token.revoke()

    assert not token_admin.display_is_active(token)
    assert not token.is_active
    assert isinstance(token.updated_at, dt.datetime)


@pytest.mark.django_db
def test_token_admin_revoke_selected(admin_user: User) -> None:
    """Test the admin bulk action revokes only active tokens."""
    active_token, _ = Token.issue(user=admin_user, name='active-token')
    revoked_token, _ = Token.issue(user=admin_user, name='revoked-token')
    revoked_token.revoke()

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
    assert not active_token.is_active
    assert not revoked_token.is_active
    message_user.assert_called_once_with(
        request,
        'Revoked 2 token(s).',
    )
