"""
Ready-to-use jwt controllers that only need a serializer.

Route one with ``as_view(serializer=...)``, there is nothing else to write.
Custom logic belongs to the reusable ``dmr.security.jwt.views`` instead.
"""

from dmr.security.jwt.concrete_views.body import (
    ObtainTokensAsyncController as ObtainTokensAsyncController,
)
from dmr.security.jwt.concrete_views.body import (
    ObtainTokensSyncController as ObtainTokensSyncController,
)
from dmr.security.jwt.concrete_views.body import (
    RefreshTokenAsyncController as RefreshTokenAsyncController,
)
from dmr.security.jwt.concrete_views.body import (
    RefreshTokenSyncController as RefreshTokenSyncController,
)
from dmr.security.jwt.concrete_views.body import (
    VerifyTokenAsyncController as VerifyTokenAsyncController,
)
from dmr.security.jwt.concrete_views.body import (
    VerifyTokenSyncController as VerifyTokenSyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    DEFAULT_REFRESH_COOKIE_PATH as DEFAULT_REFRESH_COOKIE_PATH,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieLogoutAsyncController as CookieLogoutAsyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieLogoutSyncController as CookieLogoutSyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieObtainTokensAsyncController as CookieObtainTokensAsyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieObtainTokensSyncController as CookieObtainTokensSyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieRefreshTokensAsyncController as CookieRefreshTokensAsyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieRefreshTokensSyncController as CookieRefreshTokensSyncController,
)
