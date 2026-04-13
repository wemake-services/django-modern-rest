import abc
import dataclasses
from typing import TYPE_CHECKING

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
