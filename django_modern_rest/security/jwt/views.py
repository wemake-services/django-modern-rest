import datetime as dt
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeVar

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from typing_extensions import TypedDict

from django_modern_rest import Body, Controller, ResponseSpec, modify
from django_modern_rest.errors import ErrorModel
from django_modern_rest.exceptions import NotAuthenticatedError
from django_modern_rest.security.jwt.token import JWTToken
from django_modern_rest.serializer import BaseSerializer

_ObtainTokensT = TypeVar('_ObtainTokensT', bound=Mapping[str, Any])
_TokensResponseT = TypeVar('_TokensResponseT')
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)


class ObtainTokensPayload(TypedDict):
    username: str
    password: str


class TokensResponse(TypedDict):
    access_token: str
    refresh_token: str


class _BaseTokenSettings:
    audiences: ClassVar[str | Sequence[str] | None] = None
    issuer: ClassVar[str | None] = None
    require_claims: ClassVar[Sequence[str] | None] = None
    algorithm: ClassVar[str] = 'HS256'
    expiration: ClassVar[dt.timedelta] = dt.timedelta(days=1)
    secret: ClassVar[str | None] = None
    jwt_id: ClassVar[str | None] = None
    token_cls: ClassVar[type[JWTToken]] = JWTToken


class _BaseObtainTokensSettings(_BaseTokenSettings):
    refresh_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=30)


class _BaseController(
    _BaseObtainTokensSettings,
    Controller[_SerializerT],
    Body[_ObtainTokensT],
):
    def create_token(
        self,
        expiration: dt.datetime | None = None,
        token_type: str | None = None,
    ) -> str:
        assert self.request.user.is_authenticated
        return self.token_cls(
            str(self.request.user.pk),
            exp=expiration or (dt.datetime.now(dt.UTC) + self.expiration),
            iss=self.issuer,
            aud=self.audiences,
            jti=self.jwt_id,
            extras={'type': token_type} if token_type else {},
        ).encode(
            secret=self.secret or settings.SECRET_KEY,
            algorithm=self.algorithm,
            headers=self.make_token_headers(),
        )

    def make_token_headers(self) -> dict[str, Any] | None:
        return None


class ObtainTokensSyncController(
    _BaseController[_SerializerT, _ObtainTokensT],
    Generic[_SerializerT, _ObtainTokensT, _TokensResponseT],
):
    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseSpec(
                return_type=ErrorModel,
                status_code=HTTPStatus.UNAUTHORIZED,
            ),
        ],
    )
    def post(self) -> _TokensResponseT:
        return self.login()

    def login(self) -> _TokensResponseT:
        user = authenticate(self.request, **self.parsed_body)
        if user is None:
            raise NotAuthenticatedError
        self.request.user = user
        return self.make_response_payload()

    @abstractmethod
    def make_response_payload(self) -> _TokensResponseT: ...


class ObtainTokensAsyncController(
    _BaseController[_SerializerT, _ObtainTokensT],
    Generic[_SerializerT, _ObtainTokensT, _TokensResponseT],
):
    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseSpec(
                return_type=ErrorModel,
                status_code=HTTPStatus.UNAUTHORIZED,
            ),
        ],
    )
    async def post(self) -> _TokensResponseT:
        return await self.login()

    async def login(self) -> _TokensResponseT:
        user = await aauthenticate(self.request, **self.parsed_body)
        if user is None:
            raise NotAuthenticatedError
        self.request.user = user
        return await self.make_response_payload()

    @abstractmethod
    async def make_response_payload(self) -> _TokensResponseT: ...
