import datetime as dt
from http import HTTPStatus
from typing import Final, final

import pydantic
from asgiref.sync import async_to_sync
from django.urls import reverse_lazy
from django.views.decorators.debug import sensitive_variables
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import (
    CookieJWTAsyncAuth,
    CookieJWTSyncAuth,
    HeaderJWTAsyncAuth,
    HeaderJWTSyncAuth,
    concrete_views,
)
from dmr.security.jwt.views import (  # noqa: WPS235
    CookieLogoutAsyncController,
    CookieLogoutSyncController,
    CookieObtainTokensAsyncController,
    CookieObtainTokensSyncController,
    CookieRefreshTokensAsyncController,
    CookieRefreshTokensSyncController,
    ObtainTokensAsyncController,
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
    RefreshTokenAsyncController,
    RefreshTokenPayload,
    RefreshTokenSyncController,
    VerifyTokenAsyncController,
    VerifyTokenPayload,
    VerifyTokenSyncController,
)
from server.common.assertions import check_sensitive_parameters


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
        check_sensitive_parameters(self.request)
        return payload

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = async_to_sync(self.request.auser)()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018

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
    @sensitive_variables()
    async def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        check_sensitive_parameters(self.request)
        return payload

    @override
    async def make_api_response(self) -> ObtainTokensResponse:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = await self.request.auser()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018

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
class RefreshSyncController(
    RefreshTokenSyncController[
        PydanticSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    def convert_refresh_payload(self, payload: RefreshTokenPayload) -> str:
        check_sensitive_parameters(self.request)
        return payload['refresh_token']

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = async_to_sync(self.request.auser)()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018

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
class RefreshAsyncController(
    RefreshTokenAsyncController[
        PydanticSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    @sensitive_variables()
    async def convert_refresh_payload(
        self,
        payload: RefreshTokenPayload,
    ) -> str:
        check_sensitive_parameters(self.request)
        return payload['refresh_token']

    @override
    async def make_api_response(self) -> ObtainTokensResponse:
        assert (  # noqa: S101, PT018
            self.request.user.is_authenticated and self.request.user.is_active
        )
        auser = await self.request.auser()
        assert auser.is_authenticated and auser.is_active  # noqa: S101, PT018

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
class VerifySyncController(
    VerifyTokenSyncController[
        PydanticSerializer,
        VerifyTokenPayload,
    ],
):
    @override
    def convert_verify_payload(self, payload: VerifyTokenPayload) -> str:
        check_sensitive_parameters(self.request)
        return payload['access_token']


@final
class VerifyAsyncController(
    VerifyTokenAsyncController[
        PydanticSerializer,
        VerifyTokenPayload,
    ],
):
    @override
    @sensitive_variables()
    async def convert_verify_payload(
        self,
        payload: VerifyTokenPayload,
    ) -> str:
        check_sensitive_parameters(self.request)
        return payload['access_token']


@final
class _UserOutput(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


@final
class ControllerWithJWTSyncAuth(Controller[PydanticSerializer]):
    auth = (HeaderJWTSyncAuth(),)

    def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithJWTAsyncAuth(Controller[PydanticSerializer]):
    auth = (HeaderJWTAsyncAuth(),)

    async def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithCookieJWTSyncAuth(Controller[PydanticSerializer]):
    auth = (CookieJWTSyncAuth(),)

    def get(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithCookieJWTAsyncAuth(Controller[PydanticSerializer]):
    auth = (CookieJWTAsyncAuth(),)

    async def get(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


#: Both refresh endpoints are scoped to the sync one on purpose,
#: so that a single cookie can be replayed against both of them.
_REFRESH_COOKIE_PATH: Final = reverse_lazy(
    'api:jwt_auth:jwt_cookie_refresh_sync',
)


@final
class CookieObtainSyncController(
    CookieObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
    ],
):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        check_sensitive_parameters(self.request)
        return payload


@final
class CookieObtainAsyncController(
    CookieObtainTokensAsyncController[
        PydanticSerializer,
        ObtainTokensPayload,
    ],
):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH

    @override
    @sensitive_variables()
    async def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        check_sensitive_parameters(self.request)
        return payload


@final
class CookieObtainWithBodySyncController(
    CookieObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        _UserOutput,
    ],
):
    """Shows that cookie views can still return a response body."""

    response_status_code = HTTPStatus.OK
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    def make_api_response(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class CookieRefreshSyncController(
    CookieRefreshTokensSyncController[PydanticSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH


@final
class CookieRefreshAsyncController(
    CookieRefreshTokensAsyncController[PydanticSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH


@final
class CookieLogoutSyncView(CookieLogoutSyncController[PydanticSerializer]):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH


@final
class CookieLogoutAsyncView(CookieLogoutAsyncController[PydanticSerializer]):
    jwt_refresh_cookie_path = _REFRESH_COOKIE_PATH


# Concrete views, they are used as-is, without any customizations at all:


@final
class ConcreteObtainSyncController(
    concrete_views.ObtainTokensSyncController[PydanticSerializer],
):
    """Concrete view to obtain both tokens in the body."""


@final
class ConcreteObtainAsyncController(
    concrete_views.ObtainTokensAsyncController[PydanticSerializer],
):
    """Concrete view to obtain both tokens in the body."""


@final
class ConcreteRefreshSyncController(
    concrete_views.RefreshTokenSyncController[PydanticSerializer],
):
    """Concrete view to refresh both tokens in the body."""


@final
class ConcreteRefreshAsyncController(
    concrete_views.RefreshTokenAsyncController[PydanticSerializer],
):
    """Concrete view to refresh both tokens in the body."""


@final
class ConcreteVerifySyncController(
    concrete_views.VerifyTokenSyncController[PydanticSerializer],
):
    """Concrete view to verify an access token."""


@final
class ConcreteVerifyAsyncController(
    concrete_views.VerifyTokenAsyncController[PydanticSerializer],
):
    """Concrete view to verify an access token."""


#: Concrete cookie views are scoped to the sync refresh endpoint,
#: just like the customized ones above.
_CONCRETE_REFRESH_COOKIE_PATH: Final = reverse_lazy(
    'api:jwt_auth:jwt_concrete_cookie_refresh_sync',
)


@final
class ConcreteCookieObtainSyncController(
    concrete_views.CookieObtainTokensSyncController[PydanticSerializer],
):
    """Concrete view to obtain both tokens as cookies."""

    jwt_refresh_cookie_path = _CONCRETE_REFRESH_COOKIE_PATH


@final
class ConcreteCookieObtainAsyncController(
    concrete_views.CookieObtainTokensAsyncController[PydanticSerializer],
):
    """Concrete view to obtain both tokens as cookies."""

    jwt_refresh_cookie_path = _CONCRETE_REFRESH_COOKIE_PATH


@final
class ConcreteCookieRefreshSyncController(
    concrete_views.CookieRefreshTokensSyncController[PydanticSerializer],
):
    """Concrete view to rotate both token cookies."""

    jwt_refresh_cookie_path = _CONCRETE_REFRESH_COOKIE_PATH


@final
class ConcreteCookieLogoutSyncController(
    concrete_views.CookieLogoutSyncController[PydanticSerializer],
):
    """Concrete view to drop both token cookies."""

    jwt_refresh_cookie_path = _CONCRETE_REFRESH_COOKIE_PATH
