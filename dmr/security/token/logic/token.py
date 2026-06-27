import datetime as dt
import secrets
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.crypto import salted_hmac

from dmr.types import EMPTY

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.security.token.models import Token

_RAW_TOKEN_SIZE = 32


def token_hash(raw_token: str) -> str:
    """Return HMAC-SHA256 hex digest of raw_token."""
    return salted_hmac(
        'dmr.security.token',
        raw_token,
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).hexdigest()


def token_create(
    *,
    user: 'AbstractBaseUser',
    name: str,
    expires_at: object = EMPTY,
) -> 'tuple[Token, str]':
    """Create a new token, returning ``(Token instance, raw token string)``."""
    from dmr.security.token.models import Token  # noqa: PLC0415
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    resolved_expires_at: dt.datetime | None
    if expires_at is EMPTY:
        default_expiry: dt.timedelta | None = resolve_setting(
            Settings.auth_token_default_expiry,
        )
        if default_expiry is None:
            resolved_expires_at = None
        else:
            resolved_expires_at = dt.datetime.now(dt.UTC) + default_expiry
    else:
        resolved_expires_at = expires_at  # type: ignore[assignment]

    raw_token = secrets.token_urlsafe(_RAW_TOKEN_SIZE)
    token = Token.objects.create(
        user=user,
        name=name,
        token_hash=token_hash(raw_token),
        expires_at=resolved_expires_at,
    )
    return token, raw_token


async def token_acreate(
    *,
    user: 'AbstractBaseUser',
    name: str,
    expires_at: object = EMPTY,
) -> 'tuple[Token, str]':
    """Async version of :func:`token_create`."""
    from dmr.security.token.models import Token  # noqa: PLC0415
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    resolved_expires_at: dt.datetime | None
    if expires_at is EMPTY:
        default_expiry: dt.timedelta | None = resolve_setting(
            Settings.auth_token_default_expiry,
        )
        if default_expiry is None:
            resolved_expires_at = None
        else:
            resolved_expires_at = dt.datetime.now(dt.UTC) + default_expiry
    else:
        resolved_expires_at = expires_at  # type: ignore[assignment]

    raw_token = secrets.token_urlsafe(_RAW_TOKEN_SIZE)
    token = await Token.objects.acreate(
        user=user,
        name=name,
        token_hash=token_hash(raw_token),
        expires_at=resolved_expires_at,
    )
    return token, raw_token


def token_is_expired(token: 'Token') -> bool:
    """Return True if the token has passed its expiry date."""
    if token.expires_at is None:
        return False
    return dt.datetime.now(dt.UTC) >= token.expires_at


def token_is_active(token: 'Token') -> bool:
    """Return True if the token is neither expired nor revoked."""
    return not token_is_expired(token) and token.revoked_at is None


def token_revoke(
    token: 'Token',
    *,
    at: dt.datetime | None = None,
) -> None:
    """Mark this token as revoked."""
    token.revoked_at = at or dt.datetime.now(dt.UTC)
    token.save(update_fields=['revoked_at', 'updated_at'])


async def token_arevoke(
    token: 'Token',
    *,
    at: dt.datetime | None = None,
) -> None:
    """Async version of :func:`token_revoke`."""
    token.revoked_at = at or dt.datetime.now(dt.UTC)
    await token.asave(update_fields=['revoked_at', 'updated_at'])
