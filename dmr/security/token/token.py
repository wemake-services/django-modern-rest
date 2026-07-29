import datetime as dt
from typing import Final

from django.conf import settings
from django.utils.crypto import salted_hmac
from typing_extensions import Sentinel

from dmr.settings import Settings, resolve_setting

# TODO: make easily customizable
RAW_TOKEN_SIZE: Final = 32


def get_token_hash(raw_token: str) -> str:
    """Hash the token value with the secret key."""
    return salted_hmac(
        'dmr.security.token.app',
        raw_token,
        # TODO: make `secret` customizable with the `SECRET_KEY` as the default
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).hexdigest()


def resolve_expiry(
    expires_at: dt.datetime | Sentinel | None,
) -> dt.datetime | None:
    """Resolve expiery for optional value."""
    # TODO: fix after sentinels are fully supported
    if not isinstance(expires_at, Sentinel):
        return expires_at

    default_expiry: dt.timedelta | None = resolve_setting(
        Settings.auth_token_default_expiry,
    )
    if default_expiry is None:
        return None
    return dt.datetime.now(dt.UTC) + default_expiry
