from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import CookieRefreshTokensSyncController


# You can also use `CookieRefreshTokensAsyncController` if needed:
class RefreshCookiesSyncController(
    CookieRefreshTokensSyncController[PydanticSerializer],
):
    # Must be the url this very controller is served on:
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')


# run: {"controller": "RefreshCookiesSyncController", "method": "post", "url": "/api/auth/refresh/", "url_names": {"api:jwt_refresh": "/api/auth/refresh/"}, "cookies": {"refresh_token": "$JWT_REFRESH_TOKEN", "csrftoken": "$CSRF_TOKEN"}, "headers": {"X-CSRFToken": "$CSRF_TOKEN"}, "populate_db": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "RefreshCookiesSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
