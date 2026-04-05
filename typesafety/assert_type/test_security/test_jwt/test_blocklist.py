import datetime as dt
from typing import assert_type

from django.contrib.auth.models import AbstractBaseUser

from dmr.security.jwt.blocklist.models import BlocklistedJWToken


def accepts_token(token: BlocklistedJWToken) -> None:
    assert_type(token.user, AbstractBaseUser)  # pyrefly: ignore[assert-type]
    assert_type(token.jti, str)
    assert_type(token.expires_at, dt.datetime)
