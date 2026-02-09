import datetime as dt
from typing import final

import pydantic
from typing_extensions import override

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt import JWTAsyncAuth, JWTSyncAuth
from django_modern_rest.security.jwt.views import (
    ObtainTokensAsyncController,
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
)


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
    def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_jwt_token(
                expiration=now + self.jwt_expiration,
                token_type='access',  # noqa: S106
            ),
            'refresh_token': self.create_jwt_token(
                expiration=now + self.jwt_refresh_expiration,
                token_type='refresh',  # noqa: S106
            ),
        }


class ObtainAccessAndRefreshAsyncController(
    ObtainTokensAsyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    @override
    async def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    async def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_jwt_token(
                expiration=now + self.jwt_expiration,
                token_type='access',  # noqa: S106
            ),
            'refresh_token': self.create_jwt_token(
                expiration=now + self.jwt_refresh_expiration,
                token_type='refresh',  # noqa: S106
            ),
        }


@final
class _UserOutput(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


@final
class ControllerWithJWTSyncAuth(Controller[PydanticSerializer]):
    auth = (JWTSyncAuth(),)

    def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithJWTAsyncAuth(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)

    async def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )
