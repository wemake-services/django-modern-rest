from typing import Final

import pytest
from django.utils.functional import Promise
from django.utils.translation import override

from dmr.exceptions import InternalServerError, NotAuthenticatedError

_ExceptionClass = type[InternalServerError] | type[NotAuthenticatedError]
_WRONG_LANG_CODE: Final = 'xx'


@pytest.mark.parametrize(
    'exception_cls',
    [InternalServerError, NotAuthenticatedError],
)
def test_default_message_is_lazy(*, exception_cls: _ExceptionClass) -> None:
    """Ensure default_message is wrapped with gettext_lazy."""
    assert isinstance(exception_cls.default_message, Promise)


@pytest.mark.parametrize(
    ('exception_cls', 'expected_msg'),
    [
        (InternalServerError, 'Internal server error'),
        (NotAuthenticatedError, 'Not authenticated'),
    ],
)
@pytest.mark.parametrize('language_code', ['en', _WRONG_LANG_CODE])
def test_default_message_resolves(
    *,
    exception_cls: _ExceptionClass,
    expected_msg: str,
    language_code: str,
) -> None:
    """Ensure `default_message` correct resolution and fallback."""
    with override(language_code):
        assert str(exception_cls.default_message) == expected_msg
