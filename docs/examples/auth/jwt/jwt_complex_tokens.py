import datetime as dt

from typing_extensions import TypedDict, override

from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensSyncController,
)


# Custom request and response models:
class _RequestModel(TypedDict):
    email: str
    password: str


class _TokensModel(TypedDict):
    access: str
    refresh: str


class _ResponseModel(TypedDict):
    auth: _TokensModel


# You can also use `ObtainTokensAsyncController` if needed:
class ObtainAccessAndRefreshSyncController(
    ObtainTokensSyncController[
        PydanticSerializer,
        _RequestModel,
        _ResponseModel,
    ],
):
    # Customizes the default jwt settings:
    jwt_issuer = 'my-awesome-company'
    jwt_algorithm = 'HS512'
    jwt_audiences = ('dev', 'qa')

    @override
    def convert_auth_payload(
        self,
        payload: _RequestModel,
    ) -> ObtainTokensPayload:
        return {'username': payload['email'], 'password': payload['password']}

    @override
    def make_api_response(self) -> _ResponseModel:
        now = dt.datetime.now(dt.UTC)
        access = self.create_jwt_token(
            expiration=now + self.jwt_expiration,
            token_type='access',
        )
        refresh = self.create_jwt_token(
            expiration=now + self.jwt_refresh_expiration,
            token_type='refresh',
        )
        return {
            'auth': {
                'access': access,
                'refresh': refresh,
            },
        }
