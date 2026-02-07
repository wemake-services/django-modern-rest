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
    ObtainTokensSyncController,
    TokensResponse,
)


class ObtainAccessAndRefreshSyncController(
    ObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        TokensResponse,
    ],
):
    @override
    def make_response_payload(self) -> TokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_token(
                expiration=now + self.expiration,
                token_type='access',
            ),
            'refresh_token': self.create_token(
                expiration=now + self.refresh_expiration,
                token_type='refresh',
            ),
        }


class ObtainAccessAndRefreshAsyncController(
    ObtainTokensAsyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        TokensResponse,
    ],
):
    @override
    async def make_response_payload(self) -> TokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_token(
                expiration=now + self.expiration,
                token_type='access',
            ),
            'refresh_token': self.create_token(
                expiration=now + self.refresh_expiration,
                token_type='refresh',
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
