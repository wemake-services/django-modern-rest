import datetime as dt
from typing import assert_type

from django.contrib.auth.models import AbstractBaseUser

from dmr.security.token.models import Token


def accepts_token(token: Token) -> None:
    assert_type(token.user, AbstractBaseUser)  # pyrefly: ignore[assert-type]
    assert_type(token.name, str)
    assert_type(token.token_hash, str)
    assert_type(token.expires_at, dt.datetime | None)
    assert_type(token.revoked_at, dt.datetime | None)
    assert_type(token.last_used_at, dt.datetime | None)
    assert_type(token.created_at, dt.datetime)
    assert_type(token.updated_at, dt.datetime)
