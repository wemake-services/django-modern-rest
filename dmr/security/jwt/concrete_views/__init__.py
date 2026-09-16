"""
Ready-to-use versions of everything in ``dmr.security.jwt.views``.

Every controller here is the same controller as the one
with the same name in ``dmr.security.jwt.views``,
with the default request and response bodies already plugged in.
Subclass one with your serializer type and route it, nothing else to write.

``CookieRefreshTokens*`` and ``CookieLogout*`` need no defaults at all,
so they are re-exported as-is: those names are the very same objects
as in ``dmr.security.jwt.views``. They are here
so that a whole cookie flow can be imported from a single module.
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
    CookieObtainTokensAsyncController as CookieObtainTokensAsyncController,
)
from dmr.security.jwt.concrete_views.cookie import (
    CookieObtainTokensSyncController as CookieObtainTokensSyncController,
)
from dmr.security.jwt.views import (
    CookieLogoutAsyncController as CookieLogoutAsyncController,
)
from dmr.security.jwt.views import (
    CookieLogoutSyncController as CookieLogoutSyncController,
)
from dmr.security.jwt.views import (
    CookieRefreshTokensAsyncController as CookieRefreshTokensAsyncController,
)
from dmr.security.jwt.views import (
    CookieRefreshTokensSyncController as CookieRefreshTokensSyncController,
)
