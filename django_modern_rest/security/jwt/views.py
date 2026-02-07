import datetime as dt
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

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

_TokenType: TypeAlias = Literal['access', 'refresh']


class ObtainTokensPayload(TypedDict):
    """
    Payload for default version of a jwt request body.

    Is also used as kwargs for :func:`django.contrib.auth.authenticate`.
    """

    username: str
    password: str


class ObtainTokensResponse(TypedDict):
    """Default response type for refresh token endpoint."""

    access_token: str
    refresh_token: str


class _BaseTokenSettings:
    """Collection of jwt settings that can be applied to any jwt controller."""

    audiences: ClassVar[str | Sequence[str] | None] = None
    issuer: ClassVar[str | None] = None
    require_claims: ClassVar[Sequence[str] | None] = None
    algorithm: ClassVar[str] = 'HS256'
    expiration: ClassVar[dt.timedelta] = dt.timedelta(days=1)
    secret: ClassVar[str | None] = None
    jwt_id: ClassVar[str | None] = None
    token_cls: ClassVar[type[JWTToken]] = JWTToken


class _BaseObtainTokensSettings(_BaseTokenSettings):
    """Settings that can be applied to controllers with refresh tokens."""

    refresh_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=10)


class _BaseTokenController(
    _BaseObtainTokensSettings,
    Controller[_SerializerT],
    Body[_ObtainTokensT],
):
    def create_token(
        self,
        expiration: dt.datetime | None = None,
        token_type: _TokenType | None = None,
    ) -> str:
        """Create correct jwt token of a give *expiration* and *type*."""
        # This is for mypy only:
        assert self.request.user.is_authenticated  # noqa: S101
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
        """Create jwt token headers, does nothing by default."""

    @abstractmethod
    def convert_auth_payload(
        self,
        payload: _ObtainTokensT,
    ) -> ObtainTokensPayload:
        """
        Convert your custom payload to kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports.

        Basically it needs ``username`` and ``password`` strings.
        """
        raise NotImplementedError


class ObtainTokensSyncController(
    _BaseTokenController[_SerializerT, _ObtainTokensT],
    Generic[_SerializerT, _ObtainTokensT, _TokensResponseT],
):
    """Sync controller to get access and refresh tokens."""

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
        """By default tokens are acquired on post."""
        return self.login()

    def login(self) -> _TokensResponseT:
        """Perform the sync login routine for user."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(self.parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.request.user = user
        return self.make_response_payload()

    @abstractmethod
    def make_response_payload(self) -> _TokensResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError


class ObtainTokensAsyncController(
    _BaseTokenController[_SerializerT, _ObtainTokensT],
    Generic[_SerializerT, _ObtainTokensT, _TokensResponseT],
):
    """Async controller to get access and refresh tokens."""

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
        """By default tokens are acquired on post."""
        return await self.login()

    async def login(self) -> _TokensResponseT:
        """Perform the async login routine for user."""
        user = await aauthenticate(
            self.request,
            **self.convert_auth_payload(self.parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.request.user = user
        return await self.make_response_payload()

    @abstractmethod
    async def make_response_payload(self) -> _TokensResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError
