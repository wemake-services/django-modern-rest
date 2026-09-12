from http import HTTPStatus

import pydantic
from django.urls import reverse_lazy
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import (
    CookieObtainTokensSyncController,
    ObtainTokensPayload,
)


class UserModel(pydantic.BaseModel):
    username: str


class ObtainCookiesWithBodyController(
    CookieObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
        UserModel,  # the response body type
    ],
):
    # `204 No Content` is the default,
    # a body needs a status code that allows one:
    response_status_code = HTTPStatus.OK
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    def make_api_response(self) -> UserModel:
        return UserModel(username=self.request.user.get_username())


# openapi: {"controller": "ObtainCookiesWithBodyController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
