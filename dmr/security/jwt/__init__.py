# Projects that influenced this module:
# 1. https://github.com/litestar-org/litestar
# 2. https://github.com/jazzband/djangorestframework-simplejwt

try:
    import jwt  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pyjwt` is not installed, '
        "consider using `pip install 'django-modern-rest[jwt]'`",
    )
    raise

from dmr.security.jwt.auth.base import BaseJWTAsyncAuth as BaseJWTAsyncAuth
from dmr.security.jwt.auth.base import BaseJWTSyncAuth as BaseJWTSyncAuth
from dmr.security.jwt.auth.base import request_jwt as request_jwt
from dmr.security.jwt.auth.cookie import (
    CookieJWTAsyncAuth as CookieJWTAsyncAuth,
)
from dmr.security.jwt.auth.cookie import CookieJWTSyncAuth as CookieJWTSyncAuth
from dmr.security.jwt.auth.header import (
    HeaderJWTAsyncAuth as HeaderJWTAsyncAuth,
)
from dmr.security.jwt.auth.header import HeaderJWTSyncAuth as HeaderJWTSyncAuth
from dmr.security.jwt.auth.header import JWTAsyncAuth as JWTAsyncAuth
from dmr.security.jwt.auth.header import JWTSyncAuth as JWTSyncAuth
from dmr.security.jwt.token import JWToken as JWToken
