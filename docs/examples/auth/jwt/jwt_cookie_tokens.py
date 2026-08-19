import datetime as dt
from http import HTTPStatus
from typing import Final

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.views.decorators.debug import sensitive_post_parameters
from typing_extensions import TypedDict

from dmr import Body, Controller, CookieSpec, NewCookie, ResponseSpec, validate
from dmr.decorators import endpoint_decorator
from dmr.errors import ErrorModel
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWToken
from dmr.security.jwt.views import ObtainTokensPayload


_SAMESITE: Final = 'strict'
_ACCESS_TTL: Final = dt.timedelta(minutes=10)
_REFRESH_TTL: Final = dt.timedelta(days=10)
# Refresh token is only ever sent to the refresh endpoint:
_REFRESH_PATH: Final = '/api/auth/refresh/'


# Tokens never reach the response body, they only live in `HttpOnly` cookies:
class _LoginResponse(TypedDict):
    user_id: int


class ObtainCookieTokensController(Controller[PydanticSerializer]):
    @endpoint_decorator(sensitive_post_parameters())
    @validate(
        ResponseSpec(
            _LoginResponse,
            status_code=HTTPStatus.OK,
            cookies={
                'access_token': CookieSpec(
                    httponly=True,
                    secure=True,
                    samesite=_SAMESITE,
                ),
                'refresh_token': CookieSpec(
                    httponly=True,
                    secure=True,
                    samesite=_SAMESITE,
                    path=_REFRESH_PATH,
                ),
            },
        ),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.UNAUTHORIZED),
    )
    def post(self, parsed_body: Body[ObtainTokensPayload]) -> HttpResponse:
        user = authenticate(self.request, **parsed_body)
        if user is None:
            raise NotAuthenticatedError

        now = dt.datetime.now(dt.UTC)
        return self.to_response(
            _LoginResponse(user_id=user.pk),
            status_code=HTTPStatus.OK,
            cookies={
                'access_token': NewCookie(
                    value=self._encode(user.pk, now + _ACCESS_TTL),
                    httponly=True,
                    secure=True,
                    samesite=_SAMESITE,
                ),
                'refresh_token': NewCookie(
                    value=self._encode(user.pk, now + _REFRESH_TTL),
                    httponly=True,
                    secure=True,
                    samesite=_SAMESITE,
                    path=_REFRESH_PATH,
                ),
            },
        )

    def _encode(self, user_pk: int, expiration: dt.datetime) -> str:
        return JWToken(sub=str(user_pk), exp=expiration).encode(
            secret=settings.SECRET_KEY,
            algorithm='HS256',
        )


# openapi: {"controller": "ObtainCookieTokensController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
