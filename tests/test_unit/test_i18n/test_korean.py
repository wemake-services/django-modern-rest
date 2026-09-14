import pytest
from django.db.models import Field
from django.utils.translation import gettext, override

from dmr.exceptions import (
    InternalServerError,
    NotAuthenticatedError,
    TooManyRequestsError,
)
from dmr.pagination.cursor import InvalidCursorError
from dmr.security.jwt.blocklist.models import BlocklistedJWToken
from dmr.security.token.app.models import Token

_ExceptionClass = type[
    InternalServerError
    | NotAuthenticatedError
    | TooManyRequestsError
    | InvalidCursorError
]


@pytest.mark.parametrize(
    ('exception_cls', 'expected_message'),
    [
        (InternalServerError, '서버 내부 오류가 발생했습니다.'),
        (NotAuthenticatedError, '인증되지 않았습니다.'),
        (TooManyRequestsError, '요청이 너무 많습니다.'),
        (InvalidCursorError, '유효하지 않은 커서입니다.'),
    ],
)
@pytest.mark.parametrize('language_code', ['ko', 'ko-kr'])
def test_korean_default_messages(
    *,
    exception_cls: _ExceptionClass,
    expected_message: str,
    language_code: str,
) -> None:
    """Resolve lazy error messages using the compiled Korean catalog."""
    with override(language_code):
        assert str(exception_cls.default_message) == expected_message


def test_korean_message_formatting() -> None:
    """Preserve named placeholders when translating an HTTP method error."""
    with override('ko'):
        message = gettext(
            'Method {method} is not allowed, allowed: {allowed}',
        ).format(method='DELETE', allowed=['GET', 'POST'])

    assert message == (
        "DELETE 메서드는 허용되지 않습니다. 허용된 메서드: ['GET', 'POST']"
    )


@pytest.mark.parametrize(
    ('field_name', 'expected_label'),
    [
        ('name', '이름'),
        ('token_hash', '토큰 해시'),
        ('expires_at', '만료 일시'),
        ('revoked_at', '폐기 일시'),
        ('last_used_at', '마지막 사용 일시'),
        ('created_at', '생성 일시'),
        ('updated_at', '수정 일시'),
    ],
)
def test_korean_token_field_labels(
    *,
    field_name: str,
    expected_label: str,
) -> None:
    """Translate admin field labels, distinguishing expiry from revocation."""
    field = Token._meta.get_field(field_name)
    assert isinstance(field, Field)
    with override('ko'):
        assert str(field.verbose_name) == expected_label


def test_korean_model_names() -> None:
    """Use natural Korean labels for both singular and plural model names."""
    with override('ko'):
        assert str(Token._meta.verbose_name) == '토큰'
        assert str(Token._meta.verbose_name_plural) == '토큰'
        assert str(BlocklistedJWToken._meta.verbose_name) == '차단된 JWT 토큰'
        assert str(BlocklistedJWToken._meta.verbose_name_plural) == (
            '차단된 JWT 토큰'
        )
