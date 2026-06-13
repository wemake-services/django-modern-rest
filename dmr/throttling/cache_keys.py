import abc
import dataclasses
import hashlib
from typing import TYPE_CHECKING, Literal

from typing_extensions import override

from dmr.security.jwt.auth import request_jwt

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class BaseThrottleCacheKey:
    """Base class for all cache keys."""

    runs_before_auth: bool
    name: str

    @abc.abstractmethod
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """
        Returns the cache key.

        If string is returned, we use this as a cache key.
        If ``None`` is returned, this request
        will be skipped from this exact throttling check.
        However, other keys may still be applied.
        """
        raise NotImplementedError


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class RemoteAddr(BaseThrottleCacheKey):
    """
    Uses ``REMOTE_ADDR`` from ``request.META`` as a cache key.

    .. warning::

        Be sure to correctly configure your HTTP Proxy!
        Otherwise, ``REMOTE_ADDR`` might be set incorrectly.

    .. seealso::

        See :attr:`django.http.HttpRequest.META` docs.

    """

    runs_before_auth: bool = True
    name: str = 'RemoteAddr'

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """Return ``REMOTE_ADDR`` which is a user's IP address, if it exists."""
        return controller.request.META.get('REMOTE_ADDR')


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class UserPk(BaseThrottleCacheKey):
    """
    Uses ``request.user.pk`` as a cache key.

    Returns ``None`` for users that should be excluded
    from throttling checks or when ``pk`` is not set.
    """

    # It can never be executed before `request.user` is set:
    runs_before_auth: Literal[False] = False
    name: str = 'UserPk'
    exclude_superuser: bool = True
    exclude_stuff: bool = True

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """Return ``request.user.pk`` when user should be throttled."""
        user = controller.request.user
        user_pk = getattr(user, 'pk', None)
        if (  # TODO: this is a bug in `WPS` :(
            user_pk is None  # noqa: WPS222
            or (getattr(user, 'is_superuser', False) and self.exclude_superuser)
            or (getattr(user, 'is_staff', False) and self.exclude_stuff)
        ):
            return None
        return str(user_pk)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class JwtToken(BaseThrottleCacheKey):
    """
    Uses a hash of JWT claims from ``request.__dmr_jwt__`` as a cache key.

    1. Never use a full token string for cache key generation.
    2. Prefer ``jti`` claim, fallback to ``sub`` claim.
    3. Store only SHA-256 hash, never raw claim values.

    Returns ``None`` when jwt token is not set,
    or when both ``jti`` and ``sub`` are missing.
    """

    # It can never be executed before auth, since jwt token
    # is attached by auth backends.
    runs_before_auth: Literal[False] = False
    name: str = 'JwtToken'

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """Return a hash of JWT ``jti`` / ``sub`` claims as a cache key."""
        jwt_token = request_jwt(controller.request)
        if jwt_token is None:
            return None

        jwt_id = getattr(jwt_token, 'jti', None)
        if jwt_id is not None:
            return hashlib.sha256(str(jwt_id).encode('utf-8')).hexdigest()

        jwt_sub = getattr(jwt_token, 'sub', None)
        if jwt_sub is None:
            return None

        return hashlib.sha256(str(jwt_sub).encode('utf-8')).hexdigest()
