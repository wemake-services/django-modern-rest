from typing_extensions import override

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import views
from dmr.security.token.app.models import Token


# You can also use `ObtainTokensSyncController` if needed:
class ObtainTokenAsyncController(
    views.ObtainTokenAsyncController[
        PydanticFastSerializer,
        views.ObtainTokenPayload,
        views.ObtainTokenResponse,
    ],
):
    # Specifing token_cls is required:
    token_cls = Token
    # And multiple optional configurations:
    token_algorithm = 'sha512'

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokenPayload,
    ) -> views.ObtainTokenPayload:
        return payload

    @override
    async def make_api_response(self) -> views.ObtainTokenResponse:
        assert self.request.user.is_authenticated
        return {'token': await self.issue_token(user=self.request.user)}


# run: {"controller": "ObtainTokenAsyncController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "ObtainTokenAsyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
