import abc
import dataclasses
from typing import TYPE_CHECKING, Literal

from typing_extensions import override

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class BaseThrottleCacheKey:
    """Base class for all cache keys."""

    __slots__ = ()

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

    @property
    @abc.abstractmethod
    def runs_before_auth(self) -> bool:
        """
        When this throttle check runs? Before or after auth?

        Change the default with care, because some cache key won't make
        any sense before the auth.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Name to be rendered in headers and other case.

        Customizes cache key / throttle name for some headers reports,
        like ``RateLimit-Policy``.
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

    runs_before_auth: bool = True  # pyright: ignore[reportIncompatibleMethodOverride]
    name: str = 'RemoteAddr'  # pyright: ignore[reportIncompatibleMethodOverride]

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

    exclude_superuser: bool = True
    exclude_stuff: bool = True
    name: str = 'UserPk'  # pyright: ignore[reportIncompatibleMethodOverride]

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """Return ``request.user.pk`` when user should be throttled."""
        user = controller.request.user
        is_superuser = getattr(user, 'is_superuser', False)
        is_staff = getattr(user, 'is_staff', False)
        user_pk = getattr(user, 'pk', None)
        is_excluded = (self.exclude_superuser and is_superuser) or (
            self.exclude_stuff and is_staff
        )
        if is_excluded or user_pk is None:
            return None
        return str(user_pk)

    @property
    @override
    def runs_before_auth(self) -> Literal[False]:
        return False
