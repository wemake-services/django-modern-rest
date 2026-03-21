from django.utils.functional import Promise
from django.utils.translation import override

from dmr.exceptions import (
    InternalServerError,
    NotAuthenticatedError,
    _not_authenticated_msg,
)


def test_internal_server_error_default_message_is_lazy() -> None:
    """Ensure InternalServerError.default_message uses gettext_lazy."""
    assert isinstance(
        InternalServerError.default_message,
        Promise,
    )


def test_not_authenticated_error_default_message_is_lazy() -> None:
    """Ensure NotAuthenticatedError default msg uses gettext_lazy."""
    assert isinstance(_not_authenticated_msg, Promise)


def test_internal_server_error_message_resolves_correctly() -> None:
    """Ensure InternalServerError.default_message resolves in en."""
    with override('en'):
        assert (
            str(InternalServerError.default_message) == 'Internal server error'
        )


def test_not_authenticated_error_message_resolves_correctly() -> None:
    """Ensure NotAuthenticatedError.default_message resolves in en."""
    with override('en'):
        assert str(NotAuthenticatedError()) == 'Not authenticated'


def test_internal_server_error_message_fallback_to_english() -> None:
    """Ensure InternalServerError.default_message falls back to en."""
    with override('xx'):
        assert (
            str(InternalServerError.default_message) == 'Internal server error'
        )


def test_not_authenticated_error_message_fallback_to_english() -> None:
    """Ensure NotAuthenticatedError.default_message falls back to en."""
    with override('xx'):
        assert str(NotAuthenticatedError()) == 'Not authenticated'
