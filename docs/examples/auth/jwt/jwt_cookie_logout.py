from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import CookieLogoutSyncController


# You can also use `CookieLogoutAsyncController` if needed:
class LogoutCookiesSyncController(
    CookieLogoutSyncController[PydanticSerializer],
):
    # Both cookies are dropped, so this must match the refresh controller:
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')


# openapi: {"controller": "LogoutCookiesSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
