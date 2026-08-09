import abc
import importlib
from typing import TYPE_CHECKING, Any, Generic, Self

from django.http import HttpRequest
from typing_extensions import TypeVar, override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import SecurityRequirement
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.security.token.request import set_request_attrs
from dmr.security.token.token import (
    DEFAULT_TOKEN_ALGORITHM,
    DEFAULT_TOKEN_SALT,
    TokenLikeAsync,
    TokenLikeSync,
)

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


_TokenLikeT = TypeVar(
    '_TokenLikeT',
    bound=TokenLikeSync[Any] | TokenLikeAsync[Any],
)


class _BaseTokenAuth(Generic[_TokenLikeT]):
    """
    Token auth.

    Attributes:
        security_scheme_name: Security scheme name for OpenAPI.
        token_secret: What secret should we use for token hash?
            Default to ``settings.SECRET_KEY``.
        token_salt: What salt should we use for token hash?
        token_algorithm: What algorithm should we use for token hash?

    .. note::

        ``update_last_used`` is opt-in and defaults to ``False``.
        Pass ``update_last_used=True`` to persist ``last_used_at``
        on every successful authentication. This adds an extra
        ``UPDATE`` per request, so only enable it where last-use
        tracking is actually needed.

        It is not a transactional atomic update. Why?
        1. For speed
        2. Because Django does not suppoer natice async
           transactions without a theadpool

        If you need a transaction for this, you can subclass the auth class
        and modify the ``authenticate`` and ``get_token``
        methods to work inside a transaction with ``.select_for_update()``
        on token instance.

    """

    __slots__ = (
        '_token_model',
        '_update_last_used',
        'security_scheme_name',
        'token_algorithm',
        'token_salt',
        'token_secret',
    )

    def __init__(
        self,
        *,
        security_scheme_name: str = 'token',
        update_last_used: bool = False,
        token_secret: str | None = None,
        token_salt: str = DEFAULT_TOKEN_SALT,
        token_algorithm: str = DEFAULT_TOKEN_ALGORITHM,
    ) -> None:
        self.security_scheme_name = security_scheme_name
        self._update_last_used = update_last_used
        self.token_secret = token_secret
        self.token_secret = token_secret
        self.token_salt = token_salt
        self.token_algorithm = token_algorithm
        self._token_model: type[_TokenLikeT] | None = None

    @abc.abstractmethod
    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Extract the raw token string from the request. Must be overridden."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def token_model(self) -> type[_TokenLikeT]:
        """Returns the Token model. Override to use a custom model."""
        raise NotImplementedError

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}


class BaseTokenSyncAuth(_BaseTokenAuth[TokenLikeSync[Any]], SyncAuth):  # noqa: WPS214
    """Shared sync authentication pipeline for single-source token auth."""

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Authenticate via opaque token."""
        raw_token = self.get_raw_token(controller.request)
        if raw_token is None:
            return None
        self.authenticate(controller.request, raw_token)
        return self

    def authenticate(
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = self.get_token(raw_token)
        self.check_token(token)
        user = token.get_user()
        self.check_user(user)
        if self._update_last_used:
            token.mark_used()
        self.set_request_attrs(request, user, token=token)
        return user

    @property
    @override
    def token_model(self) -> type[TokenLikeSync[Any]]:  # `Any` for subtyping
        """Return sync token model."""
        if self._token_model is not None:
            return self._token_model
        token_module = _load_default_model()
        self._token_model = token_module
        # for mypy: it can't be none at this point
        assert self._token_model  # noqa: S101
        return self._token_model

    def get_token(self, raw_token: str) -> TokenLikeSync:
        """Look up and validate the token from the DB."""
        token = self.token_model.find_raw(
            raw_token,
            token_secret=self.token_secret,
            token_salt=self.token_salt,
            token_algorithm=self.token_algorithm,
        )
        if token is None:
            raise NotAuthenticatedError
        return token

    def check_token(self, token: TokenLikeSync) -> None:
        """Raise NotAuthenticatedError if the token is not active."""
        if not token.is_active:
            raise NotAuthenticatedError

    def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: TokenLikeSync,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, token=token)


class BaseTokenAsyncAuth(_BaseTokenAuth[TokenLikeAsync[Any]], AsyncAuth):  # noqa: WPS214
    """Shared async authentication pipeline for single-source token auth."""

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Authenticate via opaque token."""
        raw_token = self.get_raw_token(controller.request)
        if raw_token is None:
            return None
        await self.authenticate(controller.request, raw_token)
        return self

    async def authenticate(  # noqa: WPS217
        self,
        request: HttpRequest,
        raw_token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        token = await self.get_token(raw_token)
        await self.check_token(token)
        user = await token.aget_user()
        await self.check_user(user)
        if self._update_last_used:
            await token.amark_used()
        await self.set_request_attrs(request, user, token=token)
        return user

    @property
    @override
    def token_model(self) -> type[TokenLikeAsync[Any]]:  # `Any` for subtyping
        """Return sync token model."""
        if self._token_model is not None:
            return self._token_model
        token_module = _load_default_model()
        self._token_model = token_module
        # for mypy: it can't be none at this point
        assert self._token_model  # noqa: S101
        return self._token_model

    async def get_token(self, raw_token: str) -> TokenLikeAsync:
        """Look up and validate the token from the DB."""
        token = await self.token_model.afind_raw(
            raw_token,
            token_secret=self.token_secret,
            token_salt=self.token_salt,
            token_algorithm=self.token_algorithm,
        )
        if token is None:
            raise NotAuthenticatedError
        return token

    async def check_token(self, token: TokenLikeAsync) -> None:
        """Raise NotAuthenticatedError if the token is not active."""
        if not token.is_active:
            raise NotAuthenticatedError

    async def check_user(self, user: 'AbstractBaseUser') -> None:
        """Raise NotAuthenticatedError if user account is not active."""
        if not user.is_active:
            raise NotAuthenticatedError

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        token: TokenLikeAsync,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, token=token)


def _load_default_model() -> Any:
    # This is needed, so we can trick the `import-linter`
    # that these two modules are independent. This is the only
    # place where they can really interact.
    return importlib.import_module('dmr.security.token.app.models').Token
