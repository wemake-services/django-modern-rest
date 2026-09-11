from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, ClassVar, Generic

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from typing_extensions import TypedDict, TypeVar

from dmr import Body, ResponseSpec, modify
from dmr.decorators import endpoint_decorator
from dmr.endpoint import ModifyAnyCallable
from dmr.errors import ErrorModel
from dmr.exceptions import NotAuthenticatedError
from dmr.security.base import NO_STORE_HEADERS
from dmr.security.jwt.auth.base import USER_LOOKUP_ERRORS, set_request_attrs
from dmr.security.jwt.token import JWToken
from dmr.security.jwt.views.base import (
    BaseRefreshTokenController,
    BaseTokenController,
    ObtainTokensPayload,
)
from dmr.serializer import BaseSerializer

#: Request body of all the controllers that authenticate a user.
_ObtainTokensT = TypeVar('_ObtainTokensT', bound=Mapping[str, Any])
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)


_RefreshTokensT = TypeVar('_RefreshTokensT', bound=Mapping[str, Any])
_VerifyTokenT = TypeVar('_VerifyTokenT', bound=Mapping[str, Any])
_TokensResponseT = TypeVar('_TokensResponseT')


class ObtainTokensResponse(TypedDict):
    """Default response type for refresh token endpoint."""

    access_token: str
    refresh_token: str


class ObtainTokensSyncController(
    BaseTokenController[_SerializerT],
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
    BaseTokenController[_SerializerT],
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


class RefreshTokenSyncController(  # noqa: WPS214
    BaseRefreshTokenController[_SerializerT],
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
        token = self._decode_and_validate_refresh_token(
            self.convert_refresh_payload(parsed_body),
        )
        user = self.get_user(token)
        self.check_auth(user, token)
        self.set_request_attrs(self.request, user)
        return self.make_api_response()

    def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
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


class RefreshTokenAsyncController(  # noqa: WPS214
    BaseRefreshTokenController[_SerializerT],
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
        token = self._decode_and_validate_refresh_token(
            await self.convert_refresh_payload(parsed_body),
        )
        user = await self.get_user(token)
        await self.check_auth(user, token)
        await self.set_request_attrs(self.request, user)
        return await self.make_api_response()

    @sensitive_variables()
    async def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    @sensitive_variables()
    async def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
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


class _BaseVerifyTokenController(BaseTokenController[_SerializerT]):
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
        self.check_auth(user, token)

    def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch user by token."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
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
        await self.check_auth(user, token)

    @sensitive_variables()
    async def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch user by token."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    @sensitive_variables()
    async def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
        """Run extra checks on the token's user, raise if something is off."""
        if not user.is_active:
            raise NotAuthenticatedError

    @abstractmethod
    async def convert_verify_payload(self, payload: _VerifyTokenT) -> str:
        """Extract the access token string from the request payload."""
        raise NotImplementedError
