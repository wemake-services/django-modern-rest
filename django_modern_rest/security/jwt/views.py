import datetime as dt
import uuid
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

    jwt_audiences: ClassVar[str | Sequence[str] | None] = None
    jwt_issuer: ClassVar[str | None] = None
    jwt_algorithm: ClassVar[str] = 'HS256'
    jwt_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=1)
    jwt_secret: ClassVar[str | None] = None
    jwt_token_cls: ClassVar[type[JWTToken]] = JWTToken


class _BaseObtainTokensSettings(_BaseTokenSettings):
    """Settings that can be applied to controllers with refresh tokens."""

    jwt_refresh_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=10)


class _BaseTokenController(
    _BaseObtainTokensSettings,
    Controller[_SerializerT],
    Body[_ObtainTokensT],
):
    def create_jwt_token(  # noqa: WPS211
        self,
        *,
        subject: str | None = None,
        issuer: str | None = None,
        audiences: str | Sequence[str] | None = None,
        expiration: dt.datetime | None = None,
        jwt_id: str | None = None,
        token_type: _TokenType | None = None,
        secret: str | None = None,
        algorithm: str | None = None,
        token_headers: dict[str, Any] | None = None,
    ) -> str:
        """Create correct jwt token of a give *expiration* and *type*."""
        return self.jwt_token_cls(
            sub=subject or str(self.request.user.pk),
            exp=expiration or (dt.datetime.now(dt.UTC) + self.jwt_expiration),
            iss=issuer or self.jwt_issuer,
            aud=audiences or self.jwt_audiences,
            jti=jwt_id or self.make_jwt_id(),
            extras={'type': token_type} if token_type else {},
        ).encode(
            secret=secret or self.jwt_secret or settings.SECRET_KEY,
            algorithm=algorithm or self.jwt_algorithm,
            headers=token_headers,
        )

    def make_jwt_id(self) -> str | None:
        """Create unique token's jwt id."""
        return uuid.uuid4().hex

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
    """
    Sync controller to get access and refresh tokens.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default access token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``
        jwt_token_cls: Possible custom JWT token class.

    See also:
        https://pyjwt.readthedocs.io/en/stable
        for all the JWT terms and options explanation.

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(status_code=HTTPStatus.OK)
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
    """
    Async controller to get access and refresh tokens.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``
        jwt_token_cls: Possible custom JWT token class.

    See also:
        https://pyjwt.readthedocs.io/en/stable
        for all the JWT terms and options explanation.

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(status_code=HTTPStatus.OK)
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
