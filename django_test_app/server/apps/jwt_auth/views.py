import datetime as dt
from typing import final

import pydantic
from asgiref.sync import async_to_sync
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWTAsyncAuth, JWTSyncAuth
from dmr.security.jwt.views import (
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

    @override
    def login(self, parsed_body: ObtainTokensPayload) -> ObtainTokensResponse:
        """This is needed only for test purpose."""
        response = super().login(parsed_body)
        # Testing:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = async_to_sync(self.request.auser)()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018
        return response


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

    @override
    async def login(
        self,
        parsed_body: ObtainTokensPayload,
    ) -> ObtainTokensResponse:
        """This is needed only for test purpose."""
        response = await super().login(parsed_body)
        # Testing:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = await self.request.auser()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018
        return response


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
