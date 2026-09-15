from typing import final

import pydantic
from django.contrib.auth.models import User
from django.views.decorators.debug import sensitive_variables
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.security.token import HeaderTokenSyncAuth, concrete_views
from dmr.security.token.app.models import Token
from dmr.security.token.views import (
    ObtainTokenAsyncController,
    ObtainTokenPayload,
    ObtainTokenResponse,
    ObtainTokenSyncController,
)
from server.apps.token_auth.models import CustomToken
from server.common.assertions import check_sensitive_parameters


@final
class CustomObtainTokenSyncController(
    ObtainTokenSyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
        User,
    ],
):
    token_cls = CustomToken

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokenPayload,
    ) -> ObtainTokenPayload:
        check_sensitive_parameters(self.request)
        return payload

    @override
    def make_api_response(self) -> ObtainTokenResponse:
        assert self.request.user.is_authenticated  # noqa: S101
        return {'token': self.issue_token(user=self.request.user)}


@final
class CustomObtainTokenAsyncController(
    ObtainTokenAsyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    token_cls = Token
    token_algorithm = 'sha512'  # noqa: S105
    token_salt = 'custom_salt'  # noqa: S105
    token_size = 64

    @override
    @sensitive_variables()
    async def convert_auth_payload(
        self,
        payload: ObtainTokenPayload,
    ) -> ObtainTokenPayload:
        check_sensitive_parameters(self.request)
        return payload

    @override
    async def make_api_response(self) -> ObtainTokenResponse:
        assert self.request.user.is_authenticated  # noqa: S101
        return {'token': await self.issue_token(user=self.request.user)}


# Concrete views, `token_cls` is the only thing they need:


@final
class ConcreteObtainTokenSyncController(
    concrete_views.ObtainTokenSyncController[PydanticFastSerializer, User],
):
    """Concrete view to issue an opaque token."""

    token_cls = CustomToken


@final
class ConcreteObtainTokenAsyncController(
    concrete_views.ObtainTokenAsyncController[PydanticFastSerializer],
):
    """Concrete view to issue an opaque token."""

    token_cls = Token


@final
class _TokenUsername(pydantic.BaseModel):
    username: str


@final
class ControllerCustomTokenSync(Controller[PydanticSerializer]):
    """This type is required for the e2e test."""

    auth = (
        HeaderTokenSyncAuth(
            token_algorithm='sha512',  # noqa: S106
            token_salt='custom_salt',  # noqa: S106
        ),
    )

    def get(self) -> _TokenUsername:
        return _TokenUsername.model_validate(
            self.request.user,
            from_attributes=True,
        )
