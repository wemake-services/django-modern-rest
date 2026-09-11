from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.blocklist import JWTokenBlocklistSyncMixin
from dmr.security.jwt.views import CookieRefreshTokensSyncController


# The mixin goes first, so its `check_auth` runs before ours:
class RefreshWithBlocklistController(
    JWTokenBlocklistSyncMixin,
    CookieRefreshTokensSyncController[PydanticSerializer],
):
    # A blocklisted refresh token cannot buy a new pair of tokens,
    # every other token still can:
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')


# openapi: {"controller": "RefreshWithBlocklistController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
