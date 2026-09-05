import datetime as dt
from typing import assert_type

from django.contrib.auth.models import AbstractBaseUser

from dmr.security.jwt.auth import HeaderJWTAsyncAuth, HeaderJWTSyncAuth
from dmr.security.jwt.blocklist import (
    JWTokenBlocklistAsyncMixin,
    JWTokenBlocklistSyncMixin,
)
from dmr.security.jwt.blocklist.models import BlocklistedJWToken
from dmr.security.jwt.token import JWToken


def accepts_token(token: BlocklistedJWToken) -> None:
    assert_type(token.user, AbstractBaseUser)  # pyrefly: ignore[assert-type]
    assert_type(token.jti, str)
    assert_type(token.expires_at, dt.datetime)


class _SyncAuth(JWTokenBlocklistSyncMixin, HeaderJWTSyncAuth):
    """Sync jwt auth with the blocklist mixin."""


class _AsyncAuth(JWTokenBlocklistAsyncMixin, HeaderJWTAsyncAuth):
    """Async jwt auth with the blocklist mixin."""


# The mixins must not shadow `__init__` of the auth class,
# all its keyword arguments are still known and checked:
_SyncAuth(auth_header='X-Api-Key', require_claims=['iss'])
_AsyncAuth(auth_header='X-Api-Key', require_claims=['iss'])

# Which also means that wrong arguments are still errors:
_SyncAuth('X-Api-Key')  # type: ignore[call-arg]  # ty: ignore[too-many-positional-arguments]
_AsyncAuth(auth_header=1)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
_SyncAuth(missing_argument=1)  # type: ignore[call-arg]  # ty: ignore[unknown-argument]


def blocklists_sync(
    auth: _SyncAuth,
    token: JWToken,
    user: AbstractBaseUser,
) -> None:
    assert_type(auth.token_jti(token), str)
    assert_type(auth.check_auth(user, token), None)
    assert_type(auth.blocklist(token), tuple[BlocklistedJWToken, bool])


async def blocklists_async(
    auth: _AsyncAuth,
    token: JWToken,
    user: AbstractBaseUser,
) -> None:
    assert_type(await auth.check_auth(user, token), None)
    assert_type(await auth.blocklist(token), tuple[BlocklistedJWToken, bool])
