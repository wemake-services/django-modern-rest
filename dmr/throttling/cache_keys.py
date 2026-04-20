import abc
import dataclasses
import hashlib
from typing import TYPE_CHECKING, Literal

from typing_extensions import override

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
    Uses a hash of ``request.__dmr_jwt__`` as a cache key.

    Returns ``None`` when jwt token is not set on a request.
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
        """Return a hash of ``request.__dmr_jwt__`` as a cache key."""
        jwt_token = getattr(controller.request, '__dmr_jwt__', None)
        if jwt_token is None:
            return None
        jwt_id = getattr(jwt_token, 'jti', None)
        raw_value = str(jwt_token if jwt_id is None else jwt_id)
        return hashlib.sha256(raw_value.encode('utf-8')).hexdigest()
