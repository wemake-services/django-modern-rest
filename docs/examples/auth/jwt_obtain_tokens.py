import datetime as dt

from typing_extensions import override

from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
)


# You can also use `ObtainTokensAsyncController` if needed:
class ObtainAccessAndRefreshSyncController(
    ObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    def make_response_payload(self) -> ObtainTokensResponse:
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
