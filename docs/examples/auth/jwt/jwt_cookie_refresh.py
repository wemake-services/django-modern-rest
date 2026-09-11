from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import CookieRefreshTokensSyncController


# You can also use `CookieRefreshTokensAsyncController` if needed:
class RefreshCookiesSyncController(
    CookieRefreshTokensSyncController[PydanticSerializer],
):
    # Must be the url this very controller is served on:
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')


# openapi: {"controller": "RefreshCookiesSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
