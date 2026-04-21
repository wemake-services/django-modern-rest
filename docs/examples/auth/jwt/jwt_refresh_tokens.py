import datetime as dt

from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import (
    ObtainTokensResponse,
    RefreshTokenSyncController,
)


# You can also use `RefreshTokenAsyncController` if needed:
class RefreshSyncController(
    RefreshTokenSyncController[
        PydanticSerializer,
        ObtainTokensResponse,
    ],
):
    @override
    def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_jwt_token(
                expiration=now + self.jwt_expiration,
                token_type='access',
            ),
            'refresh_token': self.create_jwt_token(
                expiration=now + self.jwt_refresh_expiration,
                token_type='refresh',
            ),
        }


# run: {"controller": "RefreshSyncController", "method": "post", "url": "/api/auth/refresh/", "body": {"refresh_token": "..."}, "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "RefreshSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
