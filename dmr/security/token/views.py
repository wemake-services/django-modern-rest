import datetime as dt
import uuid
from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Generic

from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from typing_extensions import Sentinel, TypedDict, TypeVar

from dmr import Body, Controller, ResponseSpec, modify
from dmr.decorators import endpoint_decorator
from dmr.errors import ErrorModel
from dmr.exceptions import NotAuthenticatedError
from dmr.security.base import NO_STORE_HEADERS
from dmr.security.token.constants import TOKEN_DEFAULT_EXPIRY
from dmr.security.token.request import set_request_attrs
from dmr.security.token.token import (
    TokenLikeAsync,
    TokenLikeSync,
    resolve_expiry,
)
from dmr.serializer import BaseSerializer
from dmr.types import EMPTY

_ObtainTokenT = TypeVar('_ObtainTokenT', bound=Mapping[str, Any])
_TokenResponseT = TypeVar('_TokenResponseT')
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)
_UserT = TypeVar('_UserT', bound='AbstractBaseUser', default='AbstractBaseUser')


class ObtainTokenPayload(TypedDict):
    """
    Payload for default version of an opaque token request body.

    Is also used as kwargs for :func:`django.contrib.auth.authenticate`.
    """

    username: str
    password: str


class ObtainTokenResponse(TypedDict):
    """Default response type for opaque token endpoint."""

    token: str


class _BaseTokenSettings(Controller[_SerializerT]):
    """Collection of token settings that can be applied to any controller."""

    token_size: int | None = None
    token_secret: str | None = None
    token_salt: str | None = None
    token_algorithm: str | None = None
    token_expiration: dt.timedelta = TOKEN_DEFAULT_EXPIRY

    def make_token_name(self) -> str:
        """Create unique token's name."""
        return uuid.uuid4().hex


class ObtainTokenSyncController(
    _BaseTokenSettings[_SerializerT],
    Generic[_SerializerT, _ObtainTokenT, _TokenResponseT, _UserT],
):
    """
    Sync controller to issue a new opaque token.

    Attributes:
        token_cls: Token class to be used.
        token_secret: Secret key to be used for the token hash.
            Defaults to ``settings.SECRET_KEY``.
        token_salt: Salt to be used for the token hash.
        token_algorithm: Salt to be used for the token hash.
            Defaults to ``sha256``.
        token_expiration: Default token expiration.

    .. versionadded:: 0.12.0
    """

    token_cls: type[TokenLikeSync[_UserT]]

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify(status_code=HTTPStatus.OK, headers=NO_STORE_HEADERS)
    def post(self, parsed_body: Body[_ObtainTokenT]) -> _TokenResponseT:
        """By default tokens are acquired on post."""
        return self.login(parsed_body)

    @sensitive_variables()
    def login(self, parsed_body: _ObtainTokenT) -> _TokenResponseT:
        """Perform the sync login routine for user."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.set_request_attrs(self.request, user)
        return self.make_api_response()

    @sensitive_variables()
    def issue_token(  # noqa: WPS211
        self,
        *,
        # Most frequent:
        user: _UserT,
        name: str | None = None,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        # Less frequent:
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> str:
        """Create correct opaque token with all possible customizations."""
        _, raw_token = self.token_cls.issue(
            user=user,
            name=name or self.make_token_name(),
            expires_at=resolve_expiry(
                expires_at,
                expiration=self.token_expiration,
            ),
            token_size=token_size or self.token_size,
            token_secret=token_secret or self.token_secret,
            token_salt=token_salt or self.token_salt,
            token_algorithm=token_algorithm or self.token_algorithm,
        )
        return raw_token

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
        payload: _ObtainTokenT,
    ) -> ObtainTokenPayload:
        """
        Convert your custom payload to kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports.

        Basically it needs ``username`` and ``password`` strings.
        """
        raise NotImplementedError

    @abstractmethod
    def make_api_response(self) -> _TokenResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError


class ObtainTokenAsyncController(
    _BaseTokenSettings[_SerializerT],
    Generic[_SerializerT, _ObtainTokenT, _TokenResponseT, _UserT],
):
    """
    Sync controller to issue a new opaque token.

    Attributes:
        token_cls: Token class to be used.
        token_secret: Secret key to be used for the token hash.
            Defaults to ``settings.SECRET_KEY``.
        token_salt: Salt to be used for the token hash.
        token_algorithm: Salt to be used for the token hash.
            Defaults to ``sha256``.

    .. versionadded:: 0.12.0
    """

    token_cls: type[TokenLikeAsync[_UserT]]

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @modify(status_code=HTTPStatus.OK, headers=NO_STORE_HEADERS)
    async def post(self, parsed_body: Body[_ObtainTokenT]) -> _TokenResponseT:
        """By default tokens are acquired on post."""
        return await self.login(parsed_body)

    @sensitive_variables()
    async def login(self, parsed_body: _ObtainTokenT) -> _TokenResponseT:
        """Perform the sync login routine for user."""
        user = await aauthenticate(
            self.request,
            **(await self.convert_auth_payload(parsed_body)),
        )
        if user is None:
            raise NotAuthenticatedError
        await self.set_request_attrs(self.request, user)
        return await self.make_api_response()

    @sensitive_variables()
    async def issue_token(  # noqa: WPS211
        self,
        *,
        # Most frequent:
        user: _UserT,
        name: str | None = None,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        # Less frequent:
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> str:
        """Create correct opaque token with all possible customizations."""
        _, raw_token = await self.token_cls.aissue(
            user=user,
            name=name or self.make_token_name(),
            expires_at=resolve_expiry(
                expires_at,
                expiration=self.token_expiration,
            ),
            token_size=token_size or self.token_size,
            token_secret=token_secret or self.token_secret,
            token_salt=token_salt or self.token_salt,
            token_algorithm=token_algorithm or self.token_algorithm,
        )
        return raw_token

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
        payload: _ObtainTokenT,
    ) -> ObtainTokenPayload:
        """
        Convert your custom payload to kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports.

        Basically it needs ``username`` and ``password`` strings.
        """
        raise NotImplementedError

    @abstractmethod
    async def make_api_response(self) -> _TokenResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError
