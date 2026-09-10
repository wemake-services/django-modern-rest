from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import CookieRefreshTokensSyncController


# You can also use `CookieRefreshTokensAsyncController` if needed:
class RefreshCookiesSyncController(
    CookieRefreshTokensSyncController[PydanticSerializer],
):
    # Must be the url this controller is served on:
    jwt_refresh_cookie_path = '/api/auth/refresh/'


# openapi: {"controller": "RefreshCookiesSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
