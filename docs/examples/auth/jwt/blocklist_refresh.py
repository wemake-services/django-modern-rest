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


# run: {"controller": "RefreshWithBlocklistController", "method": "post", "url": "/api/auth/refresh/", "url_names": {"api:jwt_refresh": "/api/auth/refresh/"}, "cookies": {"refresh_token": "$JWT_REFRESH_TOKEN", "csrftoken": "$CSRF_TOKEN"}, "headers": {"X-CSRFToken": "$CSRF_TOKEN"}, "populate_db": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "RefreshWithBlocklistController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
