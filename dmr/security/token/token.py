import abc
import datetime as dt
from typing import TYPE_CHECKING, Final, Generic, Self

from django.conf import settings
from django.utils.crypto import salted_hmac
from typing_extensions import Sentinel, TypeVar

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
        >>> from dmr.security.token import TokenLikeSync

        >>> class YourSyncToken(TokenLikeSync[CustomUser], models.Model):
        ...     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
        ...
        ...     class Meta:  # Just needed for the doctest example
        ...         app_label = 'token_auth'

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
    def issue(
        cls,
        *,
        user: _UserT,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> tuple[Self, str]:
        """Create new token."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def find_raw(cls, raw_token: str) -> Self | None:
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
        >>> from dmr.security.token import TokenLikeAsync

        >>> class YourAsyncToken(TokenLikeSync[CustomUser], models.Model):
        ...     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
        ...
        ...     class Meta:  # Just needed for the doctest example
        ...         app_label = 'token_auth'

    """

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
    async def aissue(
        cls,
        *,
        user: _UserT,
        name: str,
        expires_at: dt.datetime | Sentinel | None = EMPTY,
    ) -> tuple[Self, str]:
        """Async create new token."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def afind_raw(cls, raw_token: str) -> Self | None:
        """Async find token by its hash."""
        raise NotImplementedError


# TODO: make easily customizable
RAW_TOKEN_SIZE: Final = 32


def get_token_hash(raw_token: str) -> str:
    """Hash the token value with the secret key."""
    return salted_hmac(
        'dmr.security.token.app',
        raw_token,
        # TODO: make `secret` customizable with the `SECRET_KEY` as the default
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).hexdigest()


def resolve_expiry(
    expires_at: dt.datetime | Sentinel | None,
) -> dt.datetime | None:
    """Resolve expiery for optional value."""
    # Import cycle:
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    # TODO: fix after sentinels are fully supported
    if not isinstance(expires_at, Sentinel):
        return expires_at

    default_expiry: dt.timedelta | None = resolve_setting(
        Settings.auth_token_default_expiry,
    )
    if default_expiry is None:
        return None
    return dt.datetime.now(dt.UTC) + default_expiry
