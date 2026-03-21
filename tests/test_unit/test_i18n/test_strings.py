import pytest
from django.utils.functional import Promise
from django.utils.translation import override

from dmr.exceptions import (
    InternalServerError,
    NotAuthenticatedError,
)

_ExceptionClass = type[InternalServerError] | type[NotAuthenticatedError]

_wrong_lang_code = 'xx'


@pytest.mark.parametrize(
    ('exception_cls', 'expected'),
    [
        (InternalServerError, 'Internal server error'),
        (NotAuthenticatedError, 'Not authenticated'),
    ],
)
def test_default_message_is_lazy(
    *,
    exception_cls: _ExceptionClass,
    expected: str,
) -> None:
    """Ensure default_message is wrapped with gettext_lazy."""
    assert isinstance(exception_cls.default_message, Promise)


@pytest.mark.parametrize(
    ('exception_cls', 'expected'),
    [
        (InternalServerError, 'Internal server error'),
        (NotAuthenticatedError, 'Not authenticated'),
    ],
)
def test_default_message_resolves_in_en(
    *,
    exception_cls: _ExceptionClass,
    expected: str,
) -> None:
    """Ensure default_message resolves correctly in en."""
    with override('en'):
        assert str(exception_cls.default_message) == expected


@pytest.mark.parametrize(
    ('exception_cls', 'expected'),
    [
        (InternalServerError, 'Internal server error'),
        (NotAuthenticatedError, 'Not authenticated'),
    ],
)
def test_default_message_fallback_to_english(
    *,
    exception_cls: _ExceptionClass,
    expected: str,
) -> None:
    """Ensure default_message falls back to English."""
    with override(_wrong_lang_code):
        assert str(exception_cls.default_message) == expected
