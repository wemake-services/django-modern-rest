import abc
import datetime as dt
from typing import TYPE_CHECKING, Final, Generic, Self

from django.utils.crypto import salted_hmac
from typing_extensions import Sentinel, TypeVar

from dmr.security.token.constants import TOKEN_DEFAULT_EXPIRY
from dmr.types import EMPTY

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


class _TokenLikeBase:
    __slots__ = ()

    @property
    @abc.abstractmethod
    def is_expired(self) -> bool:
        """Is current token expired?"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def is_active(self) -> bool:
        """Is current token active?"""
        raise NotImplementedError


_UserT = TypeVar('_UserT', bound='AbstractBaseUser', default='AbstractBaseUser')


class TokenLikeSync(_TokenLikeBase, Generic[_UserT]):
    """
    Base sync interface for all token models.

    This type is generic on the user type.
    If you want to customize the ``User`` object that you are working with,
    just inherit from a generic version, like so:

    .. code:: python

        >>> from django.db import models
        >>> from django.contrib.auth.models import User as CustomUser
        >>> from dmr.security.token.token import TokenLikeSync

        >>> class YourSyncToken(TokenLikeSync[CustomUser], models.Model):
        ...     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
        ...
        ...     class Meta:  # Just needed for the doctest example
        ...         abstract = True

    .. versionadded:: 0.12.0
    """

    __slots__ = ()

    @abc.abstractmethod
    def get_user(self) -> _UserT:
        """Get user that this token belongs to."""
        raise NotImplementedError

    @abc.abstractmethod
    def mark_used(self) -> None:
        """Mark this token as used."""
        raise NotImplementedError

    @abc.abstractmethod
    def revoke(
        self,
        *,
        at: dt.datetime | None = None,
    ) -> None:
        """Revoke this token."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def issue(  # noqa: WPS211
        cls,
        *,
        user: _UserT,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> tuple[Self, str]:
        """
        Create new token.

        Parameters:
            user: ``User`` instance to store. Type annotation
                can be customized via generic type arguments.
            name: Name of the token.
            expires_at: When this token expires?
                Can be one of three: a specific date,
                ``None`` for tokens that do not expire at all,
                ``EMPTY`` to calculate the exiry relative to the current date.
            token_size: Size of the raw token in chars.
            token_secret: Secret key to be used for the token hash.
                Defaults to ``settings.SECRET_KEY``.
            token_salt: Salt to be used for the token hash.
            token_algorithm: Salt to be used for the token hash.
                Defaults to ``sha256``.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def find_raw(
        cls,
        raw_token: str,
        *,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> Self | None:
        """Find token by its hash."""
        raise NotImplementedError


class TokenLikeAsync(_TokenLikeBase, Generic[_UserT]):
    """
    Base async interface for all token models.

    This type is generic on the user type.
    If you want to customize the ``User`` object that you are working with,
    just inherit from a generic version, like so:

    .. code:: python

        >>> from django.db import models
        >>> from django.contrib.auth.models import User as CustomUser
        >>> from dmr.security.token.token import TokenLikeAsync

        >>> class YourAsyncToken(TokenLikeAsync[CustomUser], models.Model):
        ...     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
        ...
        ...     class Meta:  # Just needed for the doctest example
        ...         abstract = True

    .. versionadded:: 0.12.0
    """

    __slots__ = ()

    @abc.abstractmethod
    async def aget_user(self) -> _UserT:
        """Async get user that this token belongs to."""
        raise NotImplementedError

    @abc.abstractmethod
    async def amark_used(self) -> None:
        """Async mark this token as used."""
        raise NotImplementedError

    @abc.abstractmethod
    async def arevoke(
        self,
        *,
        at: dt.datetime | None = None,
    ) -> None:
        """Async revoke this token."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def aissue(  # noqa: WPS211
        cls,
        *,
        user: _UserT,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
        token_size: int | None = None,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> tuple[Self, str]:
        """Async version of :meth:`TokenLikeSync.issue`."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def afind_raw(
        cls,
        raw_token: str,
        *,
        token_secret: str | None = None,
        token_salt: str | None = None,
        token_algorithm: str | None = None,
    ) -> Self | None:
        """Async find token by its hash."""
        raise NotImplementedError


# TODO: make easily customizable
_RAW_TOKEN_SIZE: Final = 32
DEFAULT_TOKEN_SALT: Final = 'dmr.security.token'  # noqa: S105
DEFAULT_TOKEN_ALGORITHM: Final = 'sha256'  # noqa: S105


def get_token_hash(
    raw_token: str,
    *,
    secret: str | None,
    salt: str | None = None,
    algorithm: str | None = None,
) -> str:
    """
    Hash the token value with the secret key.

    Parameters:
        raw_token: Raw string to be hashed.
        secret: What secret should we use for token hash?
            Default to ``settings.SECRET_KEY``.
        salt: What salt should we use for token hash?
        algorithm: What algorithm should we use for token hash?

    .. versionadded:: 0.12.0
    """
    return salted_hmac(
        salt or DEFAULT_TOKEN_SALT,
        raw_token,
        secret=secret,
        algorithm=algorithm or DEFAULT_TOKEN_ALGORITHM,
    ).hexdigest()


def resolve_expiry(
    expires_at: dt.datetime | Sentinel | None,
    *,
    expiration: dt.timedelta | None = None,
) -> dt.datetime | None:
    """
    Resolve expiery for optional value.

    .. versionadded:: 0.12.0
    """
    # TODO: fix after sentinels are fully supported
    if not isinstance(expires_at, Sentinel):
        return expires_at

    resolved_expiration = expiration or TOKEN_DEFAULT_EXPIRY
    return dt.datetime.now(dt.UTC) + resolved_expiration
