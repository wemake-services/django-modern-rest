from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import (
    CookieObtainTokensSyncController,
    ObtainTokensPayload,
)


# You can also use `CookieObtainTokensAsyncController` if needed:
class ObtainCookiesSyncController(
    CookieObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
    ],
):
    # This is the url of the refresh controller below,
    # the refresh cookie is only sent there and nowhere else:
    jwt_refresh_cookie_path = '/api/auth/refresh/'

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload


# run: {"controller": "ObtainCookiesSyncController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "ObtainCookiesSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
