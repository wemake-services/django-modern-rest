import dataclasses
import datetime as dt
import uuid
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, ClassVar, Final, Generic, Literal, TypeAlias, cast

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import rotate_token
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from typing_extensions import TypedDict, TypeVar

from dmr import (
    Body,
    Controller,
    CookieSpec,
    NewCookie,
    ResponseSpec,
    modify,
    validate,
)
from dmr.decorators import endpoint_decorator
from dmr.endpoint import ModifyAnyCallable, ValidateAnyCallable
from dmr.errors import ErrorModel
from dmr.exceptions import (
    EndpointMetadataError,
    InternalServerError,
    NotAuthenticatedError,
)
from dmr.internal.csrf import ensure_csrf
from dmr.security.base import NO_STORE_HEADERS
from dmr.security.jwt.auth.base import USER_LOOKUP_ERRORS, set_request_attrs
from dmr.security.jwt.auth.cookie import (
    DEFAULT_ACCESS_COOKIE,
    DEFAULT_REFRESH_COOKIE,
)
from dmr.security.jwt.token import JWToken, JWTokenError
from dmr.serializer import BaseSerializer
from dmr.types import safe_typevar

_ObtainTokensT = TypeVar('_ObtainTokensT', bound=Mapping[str, Any])
_RefreshTokensT = TypeVar('_RefreshTokensT', bound=Mapping[str, Any])
_VerifyTokenT = TypeVar('_VerifyTokenT', bound=Mapping[str, Any])
_TokensResponseT = TypeVar('_TokensResponseT')
#: Cookie views send their tokens in cookies, the body is empty by default.
_CookieResponseT = TypeVar('_CookieResponseT', default=None)
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

_TokenType: TypeAlias = Literal['access', 'refresh']
_SameSite: TypeAlias = Literal['lax', 'strict', 'none']

# `_CookieResponseT` as a value, so it can be passed to `ResponseSpec`.
# It is resolved to the real type of each final controller later on:
_COOKIE_RESPONSE_TYPE: Final = safe_typevar('_CookieResponseT')

# `@validate` describes headers and sets them by hand,
# both parts are built from `NO_STORE_HEADERS`, so they can't diverge:
_NO_STORE_SPEC: Final = MappingProxyType({
    header_name: header.to_spec()
    for header_name, header in NO_STORE_HEADERS.items()
})
_NO_STORE_VALUES: Final = MappingProxyType({
    header_name: header.value
    for header_name, header in NO_STORE_HEADERS.items()
})


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
    @sensitive_variables()
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
        token = self.jwt_token_cls(
            sub=subject or str(self.request.user.pk),
            exp=expiration or (dt.datetime.now(dt.UTC) + self.jwt_expiration),
            iss=issuer or self.jwt_issuer,
            aud=audiences or self.jwt_audiences,
            jti=jwt_id or self.make_jwt_id(),
            extras={'type': token_type} if token_type else {},
        )
        try:
            return token.encode(
                secret=secret or self.jwt_secret or settings.SECRET_KEY,
                algorithm=algorithm or self.jwt_algorithm,
                headers=token_headers,
            )
        except JWTokenError as exc:
            # Convert the token-layer semantic error at the HTTP boundary.
            raise InternalServerError('Failed to encode token') from exc

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
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    See also:
        https://pyjwt.readthedocs.io/en/stable
        for all the JWT terms and options explanation.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.OK
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    def post(self, parsed_body: Body[_ObtainTokensT]) -> _TokensResponseT:
        """By default tokens are acquired on post."""
        return self.login(parsed_body)

    @sensitive_variables()
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
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    See also:
        https://pyjwt.readthedocs.io/en/stable
        for all the JWT terms and options explanation.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.OK
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    async def post(self, parsed_body: Body[_ObtainTokensT]) -> _TokensResponseT:
        """By default tokens are acquired on post."""
        return await self.login(parsed_body)

    @sensitive_variables()
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

    @sensitive_variables()
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
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.OK
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec for sync verify tokens controller."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    def post(self, parsed_body: Body[_RefreshTokensT]) -> _TokensResponseT:
        """Refresh tokens on POST."""
        return self.refresh(parsed_body)

    @sensitive_variables()
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
        except USER_LOOKUP_ERRORS:
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
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.OK
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec for async refresh tokens controller."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    async def post(
        self,
        parsed_body: Body[_RefreshTokensT],
    ) -> _TokensResponseT:
        """Refresh tokens on POST."""
        return await self.refresh(parsed_body)

    @sensitive_variables()
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
        except USER_LOOKUP_ERRORS:
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


class VerifyTokenPayload(TypedDict):
    """Default request body type for the verify token endpoint."""

    access_token: str


class _BaseVerifyTokenController(_BaseTokenController[_SerializerT]):
    jwt_user_id_field: ClassVar[str] = 'pk'

    @sensitive_variables()
    def _decode_and_validate_access_token(self, encoded_token: str) -> JWToken:
        token = self.jwt_token_cls.decode(
            encoded_token=encoded_token,
            secret=self.jwt_secret or settings.SECRET_KEY,
            algorithm=self.jwt_algorithm,
            accepted_audiences=self.jwt_audiences,
            accepted_issuers=self.jwt_issuer,
        )
        if token.extras.get('type') != 'access':
            raise NotAuthenticatedError
        return token


class VerifyTokenSyncController(
    _BaseVerifyTokenController[_SerializerT],
    Generic[_SerializerT, _VerifyTokenT],
):
    """
    Sync controller to verify an access token.

    Accepts an access token in the request body, decodes and validates it,
    ensures it is an access token (not a refresh token), and confirms that
    the token subject belongs to an existing, active user.

    Returns an empty ``204 No Content`` response when the token is valid.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec for sync verify tokens controller."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    def post(self, parsed_body: Body[_VerifyTokenT]) -> None:
        """Verify the token on POST."""
        self.verify(parsed_body)

    @sensitive_variables()
    def verify(self, parsed_body: _VerifyTokenT) -> None:
        """Validate the access token and load its user."""
        token = self._decode_and_validate_access_token(
            self.convert_verify_payload(parsed_body),
        )
        user = self.get_user(token)
        self.check_auth(user)

    def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch user by token."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(self, user: Any) -> None:
        """Run extra checks on the token's user, raise if something is off."""
        if not user.is_active:
            raise NotAuthenticatedError

    @abstractmethod
    def convert_verify_payload(self, payload: _VerifyTokenT) -> str:
        """Extract the access token string from the request payload."""
        raise NotImplementedError


class VerifyTokenAsyncController(
    _BaseVerifyTokenController[_SerializerT],
    Generic[_SerializerT, _VerifyTokenT],
):
    """
    Async controller to verify an access token.

    Accepts an access token in the request body, decodes and validates it,
    ensures it is an access token (not a refresh token), and confirms that
    the token subject belongs to an existing, active user.

    Returns an empty ``204 No Content`` response when the token is valid.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default token expiration timedelta.
        jwt_refresh_expiration: Default refresh token expiration timedelta.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionchanged:: 0.15.0
        Now using ``@modify.lazy`` with the ability to change the spec.

    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def modify_spec(cls) -> ModifyAnyCallable:
        """Lazy endpoint spec for async verify tokens controller."""
        return modify(
            status_code=cls.response_status_code,
            headers=NO_STORE_HEADERS,
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify.lazy(modify_spec)
    async def post(self, parsed_body: Body[_VerifyTokenT]) -> None:
        """Verify the token on POST."""
        await self.verify(parsed_body)

    @sensitive_variables()
    async def verify(self, parsed_body: _VerifyTokenT) -> None:
        """Validate the access token and load its user."""
        token = self._decode_and_validate_access_token(
            await self.convert_verify_payload(parsed_body),
        )
        user = await self.get_user(token)
        await self.check_auth(user)

    async def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch user by token."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    async def check_auth(self, user: Any) -> None:
        """Run extra checks on the token's user, raise if something is off."""
        if not user.is_active:
            raise NotAuthenticatedError

    @abstractmethod
    async def convert_verify_payload(self, payload: _VerifyTokenT) -> str:
        """Extract the access token string from the request payload."""
        raise NotImplementedError


class _BaseCookieTokensController(  # noqa: WPS214
    _BaseTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Base for all the controllers that issue jwt tokens as cookies.

    Cookie flags are the whole security surface of this flow,
    so we pick safe defaults and never let the description
    and the actual cookie diverge: both are built
    from the same :class:`~dmr.cookies.CookieSpec` instance.

    Attributes:
        jwt_access_cookie: Name of the cookie with the access token.
            Must match ``cookie_name``
            of :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth`
            that reads it back.
        jwt_refresh_cookie: Name of the cookie with the refresh token.
        jwt_access_cookie_path: ``path`` of the access token cookie,
            it is sent to your whole API by default.
        jwt_refresh_cookie_path: ``path`` of the refresh token cookie.
            Has no default on purpose: set it to the url of the endpoint
            that refreshes tokens, so the refresh token is not sent
            with any other request. Pass ``'/'`` to send it everywhere.
        jwt_cookie_domain: ``domain`` of both cookies.
        jwt_cookie_secure: Only send both cookies over https.
        jwt_cookie_httponly: Hide both cookies from javascript.
        jwt_cookie_samesite: ``samesite`` policy of both cookies.
            Do not weaken it to ``'none'`` unless your frontend
            really is on another site.
        jwt_ensure_csrf: Run the CSRF check on endpoints that act
            on cookies alone, without any credentials in the body.

    .. versionadded:: 0.15.0
    """

    jwt_access_cookie: ClassVar[str] = DEFAULT_ACCESS_COOKIE
    jwt_refresh_cookie: ClassVar[str] = DEFAULT_REFRESH_COOKIE
    jwt_access_cookie_path: ClassVar[str] = '/'
    jwt_refresh_cookie_path: ClassVar[str | None] = None
    jwt_cookie_domain: ClassVar[str | None] = None
    jwt_cookie_secure: ClassVar[bool] = True
    jwt_cookie_httponly: ClassVar[bool] = True
    jwt_cookie_samesite: ClassVar[_SameSite] = 'lax'
    jwt_ensure_csrf: ClassVar[bool] = True

    @classmethod
    def access_cookie_spec(cls) -> CookieSpec:
        """Describes the cookie that carries the access token."""
        return CookieSpec(
            path=cls.jwt_access_cookie_path,
            max_age=int(cls.jwt_expiration.total_seconds()),
            domain=cls.jwt_cookie_domain,
            secure=cls.jwt_cookie_secure,
            httponly=cls.jwt_cookie_httponly,
            samesite=cls.jwt_cookie_samesite,
            description='Access token, sent with every API request.',
        )

    @classmethod
    def refresh_cookie_spec(cls) -> CookieSpec:
        """
        Describes the cookie that carries the refresh token.

        Raises:
            EndpointMetadataError: When ``jwt_refresh_cookie_path``
                is not set by the final controller.

        """
        if cls.jwt_refresh_cookie_path is None:
            raise EndpointMetadataError(
                f'{cls.__qualname__!r} must define `jwt_refresh_cookie_path`, '
                'it is the url path of your refresh endpoint. '
                'Scoping the refresh cookie to it keeps the refresh token '
                'out of all the other requests. '
                "Use '/' to send it everywhere.",
            )
        return CookieSpec(
            path=cls.jwt_refresh_cookie_path,
            max_age=int(cls.jwt_refresh_expiration.total_seconds()),
            domain=cls.jwt_cookie_domain,
            secure=cls.jwt_cookie_secure,
            httponly=cls.jwt_cookie_httponly,
            samesite=cls.jwt_cookie_samesite,
            description='Refresh token, only sent to the refresh endpoint.',
        )

    @classmethod
    def issued_cookies_spec(cls) -> dict[str, CookieSpec]:
        """Describes both token cookies of a successful response."""
        return {
            cls.jwt_access_cookie: cls.access_cookie_spec(),
            cls.jwt_refresh_cookie: cls.refresh_cookie_spec(),
        }

    @classmethod
    def discarded_cookies_spec(cls) -> dict[str, CookieSpec]:
        """Describes both token cookies as they are sent on logout."""
        return {
            cookie_name: dataclasses.replace(
                cookie_spec,
                max_age=0,
                description='Sent back empty and expired, so it is dropped.',
            )
            for cookie_name, cookie_spec in cls.issued_cookies_spec().items()
        }

    @classmethod
    def csrf_cookie_spec(cls) -> dict[str, CookieSpec]:
        """
        Describes the CSRF cookie that Django sets after us.

        It is written by :class:`django.middleware.csrf.CsrfViewMiddleware`
        once we rotate the token, which happens after our own validation.
        That is why it is only documented and never validated.
        With ``CSRF_USE_SESSIONS`` there is no such cookie at all.
        """
        if settings.CSRF_USE_SESSIONS:
            return {}
        return {
            settings.CSRF_COOKIE_NAME: CookieSpec(
                skip_validation=True,
                description='CSRF protection.',
            ),
        }

    @classmethod
    def csrf_response_specs(cls) -> tuple[ResponseSpec, ...]:
        """Describes the response of a failed CSRF check."""
        if not cls.jwt_ensure_csrf:
            return ()
        return (
            ResponseSpec(
                return_type=cls.error_model,
                status_code=HTTPStatus.FORBIDDEN,
                description='Raised when CSRF check failed',
            ),
        )

    def check_csrf(self) -> None:
        """
        Enforce CSRF for requests that are authed by a cookie alone.

        The browser sends these cookies on its own, so without this check
        any other site could refresh or drop the tokens of our users.
        Set ``jwt_ensure_csrf`` to ``False`` to opt out.
        """
        if self.jwt_ensure_csrf:
            ensure_csrf(self)

    @sensitive_variables()
    def issue_cookies(self) -> dict[str, NewCookie]:
        """Create both token cookies for the user of the current request."""
        now = dt.datetime.now(dt.UTC)
        return {
            self.jwt_access_cookie: NewCookie.from_spec(
                self.access_cookie_spec(),
                value=self.create_jwt_token(
                    expiration=now + self.jwt_expiration,
                    token_type='access',  # noqa: S106
                ),
            ),
            self.jwt_refresh_cookie: NewCookie.from_spec(
                self.refresh_cookie_spec(),
                value=self.create_jwt_token(
                    expiration=now + self.jwt_refresh_expiration,
                    token_type='refresh',  # noqa: S106
                ),
            ),
        }

    def discard_cookies(self) -> dict[str, NewCookie]:
        """Create empty cookies, so the browser drops the tokens right away."""
        discarded = self.discarded_cookies_spec()
        return {
            cookie_name: NewCookie.from_spec(cookie_spec, value='')
            for cookie_name, cookie_spec in discarded.items()
        }

    def rotate_csrf_token(self) -> None:
        """
        Issue a new CSRF token for the freshly authed user.

        This is what :func:`django.contrib.auth.login` does as well.
        Our cookie auth checks CSRF on every request it authenticates,
        and the frontend needs a fresh token to pass that check.
        """
        rotate_token(self.request)

    def get_cookie_token(self, cookie_name: str) -> str:
        """
        Read a raw jwt token from the given cookie.

        Raises:
            NotAuthenticatedError: When the cookie is missing or empty.

        """
        encoded_token = self.request.COOKIES.get(cookie_name)
        if not encoded_token:
            raise NotAuthenticatedError
        return encoded_token


class _BaseCookieTokensSyncController(
    _BaseCookieTokensController[_SerializerT, _CookieResponseT],
):
    """Sync half of the cookie controllers."""

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Mark the user of this request as authenticated."""
        set_request_attrs(request, user)

    def make_api_response(self) -> _CookieResponseT:
        """
        Build the response body that is sent next to the cookies.

        Empty by default: the tokens are already in the cookies,
        and sending them in the body as well would hand them
        to any script on the page, undoing ``httponly``.

        Change the response status code from ``204`` when you return a body.
        """
        return cast(_CookieResponseT, None)


class _BaseCookieTokensAsyncController(
    _BaseCookieTokensController[_SerializerT, _CookieResponseT],
):
    """Async half of the cookie controllers."""

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Mark the user of this request as authenticated."""
        set_request_attrs(request, user)

    async def make_api_response(self) -> _CookieResponseT:
        """
        Build the response body that is sent next to the cookies.

        Empty by default: the tokens are already in the cookies,
        and sending them in the body as well would hand them
        to any script on the page, undoing ``httponly``.

        Change the response status code from ``204`` when you return a body.
        """
        return cast(_CookieResponseT, None)


class CookieObtainTokensSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
    Generic[_SerializerT, _ObtainTokensT, _CookieResponseT],
):
    """
    Sync controller to issue access and refresh tokens as cookies.

    Works like :class:`~dmr.security.jwt.views.ObtainTokensSyncController`,
    but the tokens are set as cookies
    for :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth` to read them back,
    instead of being returned in the response body.

    Setting ``jwt_refresh_cookie_path`` to the url
    of your refresh endpoint is required, everything else has a default.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default access token expiration timedelta,
            it is also the ``max-age`` of the access cookie.
        jwt_refresh_expiration: Default refresh token expiration timedelta,
            it is also the ``max-age`` of the refresh cookie.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie login controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies={
                    **cls.issued_cookies_spec(),
                    **cls.csrf_cookie_spec(),
                },
            ),
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @validate.lazy(validate_spec)
    def post(self, parsed_body: Body[_ObtainTokensT]) -> HttpResponse:
        """By default cookies are acquired on post."""
        return self.login(parsed_body)

    @sensitive_variables()
    def login(self, parsed_body: _ObtainTokensT) -> HttpResponse:
        """Perform the sync login routine and set the token cookies."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.set_request_attrs(self.request, user)
        self.rotate_csrf_token()
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.issue_cookies(),
        )

    @abstractmethod
    def convert_auth_payload(
        self,
        payload: _ObtainTokensT,
    ) -> ObtainTokensPayload:
        """
        Convert your custom payload to the kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports, basically it needs
        ``username`` and ``password`` strings.
        """
        raise NotImplementedError


class CookieObtainTokensAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
    Generic[_SerializerT, _ObtainTokensT, _CookieResponseT],
):
    """
    Async controller to issue access and refresh tokens as cookies.

    Works like :class:`~dmr.security.jwt.views.ObtainTokensAsyncController`,
    but the tokens are set as cookies
    for :class:`~dmr.security.jwt.auth.CookieJWTAsyncAuth` to read them back,
    instead of being returned in the response body.

    Setting ``jwt_refresh_cookie_path`` to the url
    of your refresh endpoint is required, everything else has a default.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default access token expiration timedelta,
            it is also the ``max-age`` of the access cookie.
        jwt_refresh_expiration: Default refresh token expiration timedelta,
            it is also the ``max-age`` of the refresh cookie.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie login controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies={
                    **cls.issued_cookies_spec(),
                    **cls.csrf_cookie_spec(),
                },
            ),
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @validate.lazy(validate_spec)
    async def post(self, parsed_body: Body[_ObtainTokensT]) -> HttpResponse:
        """By default cookies are acquired on post."""
        return await self.login(parsed_body)

    @sensitive_variables()
    async def login(self, parsed_body: _ObtainTokensT) -> HttpResponse:
        """Perform the async login routine and set the token cookies."""
        user = await aauthenticate(
            self.request,
            **(await self.convert_auth_payload(parsed_body)),
        )
        if user is None:
            raise NotAuthenticatedError
        await self.set_request_attrs(self.request, user)
        self.rotate_csrf_token()
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.issue_cookies(),
        )

    @abstractmethod
    async def convert_auth_payload(
        self,
        payload: _ObtainTokensT,
    ) -> ObtainTokensPayload:
        """
        Convert your custom payload to the kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports, basically it needs
        ``username`` and ``password`` strings.
        """
        raise NotImplementedError


class CookieRefreshTokensSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
    _BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to rotate both token cookies.

    Reads the refresh token from its cookie, validates it,
    loads the user, and sets a brand new pair of cookies.
    There is no request body: the browser sends the cookie on its own,
    which is also why we check CSRF here.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
    for the rest of the settings.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie refresh controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies=cls.issued_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    def post(self) -> HttpResponse:
        """Rotate both cookies on post."""
        return self.refresh()

    @sensitive_variables()
    def refresh(self) -> HttpResponse:
        """Validate the refresh cookie, load user, and set new cookies."""
        self.check_csrf()
        token = self._decode_and_validate_refresh_token(
            self.get_cookie_token(self.jwt_refresh_cookie),
        )
        user = self.get_user(token)
        self.check_auth(user)
        self.set_request_attrs(self.request, user)
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.issue_cookies(),
        )

    def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(self, user: Any) -> None:
        """Run extra checks on the refreshing user, raise to reject."""
        if not user.is_active:
            raise NotAuthenticatedError


class CookieRefreshTokensAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
    _BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Async controller to rotate both token cookies.

    Reads the refresh token from its cookie, validates it,
    loads the user, and sets a brand new pair of cookies.
    There is no request body: the browser sends the cookie on its own,
    which is also why we check CSRF here.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensAsyncController`
    for the rest of the settings.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie refresh controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies=cls.issued_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    async def post(self) -> HttpResponse:
        """Rotate both cookies on post."""
        return await self.refresh()

    @sensitive_variables()
    async def refresh(self) -> HttpResponse:
        """Validate the refresh cookie, load user, and set new cookies."""
        self.check_csrf()
        token = self._decode_and_validate_refresh_token(
            self.get_cookie_token(self.jwt_refresh_cookie),
        )
        user = await self.get_user(token)
        await self.check_auth(user)
        await self.set_request_attrs(self.request, user)
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.issue_cookies(),
        )

    async def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    async def check_auth(self, user: Any) -> None:
        """Run extra checks on the refreshing user, raise to reject."""
        if not user.is_active:
            raise NotAuthenticatedError


class CookieLogoutSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to drop both token cookies.

    Sends both cookies back empty and already expired,
    so the browser drops them right away.
    It is transport-only: a token that leaked before the logout
    stays valid until it expires. Override :meth:`revoke_tokens`
    to also put it into the blocklist,
    see :ref:`blocklisting-tokens`.

    There is no request body, which is why we check CSRF here.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie logout controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies=cls.discarded_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @validate.lazy(validate_spec)
    def post(self) -> HttpResponse:
        """By default cookies are dropped on post."""
        return self.logout()

    def logout(self) -> HttpResponse:
        """Perform the sync logout routine and drop the token cookies."""
        self.check_csrf()
        self.revoke_tokens()
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.discard_cookies(),
        )

    def revoke_tokens(self) -> None:
        """
        Hook to invalidate the tokens we are logging out of.

        Does nothing by default, because the blocklist app is optional.
        With it installed, blocklist
        :func:`~dmr.security.jwt.auth.request_jwt` of this request.
        """


class CookieLogoutAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to drop both token cookies.

    Sends both cookies back empty and already expired,
    so the browser drops them right away.
    It is transport-only: a token that leaked before the logout
    stays valid until it expires. Override :meth:`revoke_tokens`
    to also put it into the blocklist,
    see :ref:`blocklisting-tokens`.

    There is no request body, which is why we check CSRF here.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie logout controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=_NO_STORE_SPEC,
                cookies=cls.discarded_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @validate.lazy(validate_spec)
    async def post(self) -> HttpResponse:
        """By default cookies are dropped on post."""
        return await self.logout()

    async def logout(self) -> HttpResponse:
        """Perform the async logout routine and drop the token cookies."""
        self.check_csrf()
        await self.revoke_tokens()
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=_NO_STORE_VALUES,
            cookies=self.discard_cookies(),
        )

    async def revoke_tokens(self) -> None:
        """
        Hook to invalidate the tokens we are logging out of.

        Does nothing by default, because the blocklist app is optional.
        With it installed, blocklist
        :func:`~dmr.security.jwt.auth.request_jwt` of this request.
        """
