import datetime as dt
import uuid
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from typing_extensions import TypedDict

from dmr import Body, Controller, ResponseSpec, modify
from dmr.errors import ErrorModel
from dmr.exceptions import NotAuthenticatedError
from dmr.security.jwt.auth import set_request_attrs
from dmr.security.jwt.token import JWToken
from dmr.serializer import BaseSerializer

_ObtainTokensT = TypeVar('_ObtainTokensT', bound=Mapping[str, Any])
_RefreshTokensT = TypeVar('_RefreshTokensT', bound=Mapping[str, Any])
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
    jwt_token_cls: ClassVar[type[JWToken]] = JWToken


class _BaseObtainTokensSettings(_BaseTokenSettings):
    """Settings that can be applied to controllers with refresh tokens."""

    jwt_refresh_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=10)


class _BaseTokenController(
    _BaseObtainTokensSettings,
    Controller[_SerializerT],
):
    def create_jwt_token(  # noqa: WPS211
        self,
        *,
        # Most frequent:
        expiration: dt.datetime | None = None,
        token_type: _TokenType | None = None,
        # Less frequent:
        subject: str | None = None,
        issuer: str | None = None,
        audiences: str | Sequence[str] | None = None,
        jwt_id: str | None = None,
        secret: str | None = None,
        algorithm: str | None = None,
        token_headers: dict[str, Any] | None = None,
    ) -> str:
        """Create correct jwt token of a given *expiration* and *token_type*."""
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


class ObtainTokensSyncController(
    _BaseTokenController[_SerializerT],
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
    def post(self, parsed_body: Body[_ObtainTokensT]) -> _TokensResponseT:
        """By default tokens are acquired on post."""
        return self.login(parsed_body)

    def login(self, parsed_body: _ObtainTokensT) -> _TokensResponseT:
        """Perform the sync login routine for user."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.set_request_attrs(self.request, user)
        return self.make_api_response()

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user)

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

    @abstractmethod
    def make_api_response(self) -> _TokensResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError


class ObtainTokensAsyncController(
    _BaseTokenController[_SerializerT],
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
    async def post(self, parsed_body: Body[_ObtainTokensT]) -> _TokensResponseT:
        """By default tokens are acquired on post."""
        return await self.login(parsed_body)

    async def login(self, parsed_body: _ObtainTokensT) -> _TokensResponseT:
        """Perform the async login routine for user."""
        user = await aauthenticate(
            self.request,
            **(await self.convert_auth_payload(parsed_body)),
        )
        if user is None:
            raise NotAuthenticatedError
        await self.set_request_attrs(self.request, user)
        return await self.make_api_response()

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user)

    @abstractmethod
    async def convert_auth_payload(
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

    @abstractmethod
    async def make_api_response(self) -> _TokensResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError


class RefreshTokenPayload(TypedDict):
    """Default request body type for the refresh token endpoint."""

    refresh_token: str


class _BaseRefreshTokenController(_BaseTokenController[_SerializerT]):
    jwt_user_id_field: ClassVar[str] = 'pk'

    def _decode_and_validate_refresh_token(self, encoded_token: str) -> JWToken:
        token = self.jwt_token_cls.decode(
            encoded_token=encoded_token,
            secret=self.jwt_secret or settings.SECRET_KEY,
            algorithm=self.jwt_algorithm,
            accepted_audiences=self.jwt_audiences,
            accepted_issuers=self.jwt_issuer,
        )
        if token.extras.get('type') != 'refresh':
            raise NotAuthenticatedError
        return token


class RefreshTokenSyncController(
    _BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _RefreshTokensT, _TokensResponseT],
):
    """
    Sync controller to refresh access and refresh tokens.

    Accepts a refresh token in the request body, validates it,
    loads the user, and calls :meth:`make_api_response` to build the response.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``
        jwt_token_cls: Possible custom JWT token class.

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(status_code=HTTPStatus.OK)
    def post(self, parsed_body: Body[_RefreshTokensT]) -> _TokensResponseT:
        """Refresh tokens on POST."""
        return self.refresh(parsed_body)

    def refresh(self, parsed_body: _RefreshTokensT) -> _TokensResponseT:
        """Validate the refresh token, load user, and return new tokens."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        token = self._decode_and_validate_refresh_token(
            self.convert_refresh_payload(parsed_body),
        )
        try:
            user = get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
        self.check_auth(user)
        self.set_request_attrs(self.request, user)
        return self.make_api_response()

    def check_auth(self, user: Any) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Apply authed user to the current request."""
        set_request_attrs(request, user)

    @abstractmethod
    def convert_refresh_payload(self, payload: _RefreshTokensT) -> str:
        """Extract the refresh token string from the request payload."""
        raise NotImplementedError

    @abstractmethod
    def make_api_response(self) -> _TokensResponseT:
        """Build the token pair response after a successful refresh."""
        raise NotImplementedError


class RefreshTokenAsyncController(
    _BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _RefreshTokensT, _TokensResponseT],
):
    """
    Async controller to refresh access and refresh tokens.

    Accepts a refresh token in the request body, validates it,
    loads the user, and calls :meth:`make_api_response` to build the response.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``
        jwt_token_cls: Possible custom JWT token class.

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(status_code=HTTPStatus.OK)
    async def post(
        self,
        parsed_body: Body[_RefreshTokensT],
    ) -> _TokensResponseT:
        """Refresh tokens on POST."""
        return await self.refresh(parsed_body)

    async def refresh(
        self,
        parsed_body: _RefreshTokensT,
    ) -> _TokensResponseT:
        """Validate the refresh token, load user, and return new tokens."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        token = self._decode_and_validate_refresh_token(
            await self.convert_refresh_payload(parsed_body),
        )
        try:
            user = await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
        await self.check_auth(user)
        await self.set_request_attrs(self.request, user)
        return await self.make_api_response()

    async def check_auth(self, user: Any) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Apply authed user to the current request."""
        set_request_attrs(request, user)

    @abstractmethod
    async def convert_refresh_payload(self, payload: _RefreshTokensT) -> str:
        """Extract the refresh token string from the request payload."""
        raise NotImplementedError

    @abstractmethod
    async def make_api_response(self) -> _TokensResponseT:
        """Build the token pair response after a successful refresh."""
        raise NotImplementedError
