import abc
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import TypedDict

from dmr.exceptions import EndpointMetadataError

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer
    from dmr.throttling import AsyncThrottle, SyncThrottle
    from dmr.throttling.algorithms import BaseThrottleAlgorithm


class CachedRateLimit(TypedDict):
    """Representation of a cached object's metadata."""

    # We usually store `int(time.time())` result here:
    time: int
    # We overly complicate the storage a bit, because this design
    # allows future potential algorithms to store requests as lists,
    # if it is needed.
    history: list[int]


class _BaseThrottleBackend:
    """Common logic for all kinds of backends."""

    #: Format name that the backend needs:
    needs_transaction_script: ClassVar[str | None] = None

    __slots__ = ()

    def unsupported_format(
        self,
        algorithm: 'BaseThrottleAlgorithm',
    ) -> str | None:
        """Check whether this algorithm is supported by this backend."""
        if self.needs_transaction_script and (
            algorithm.transaction_script(self.needs_transaction_script) is None
        ):
            return self.needs_transaction_script
        return None

    def initialize_algorithm(self, algorithm: 'BaseThrottleAlgorithm') -> None:
        """Initialize and prepare backend for the algorithm."""
        # Do the validation:
        script_format = self.unsupported_format(algorithm)
        if script_format:
            raise EndpointMetadataError(
                f'Cannot use backend {self!r} with {algorithm!r}, '
                f'because backend requires {script_format} transactional '
                'script support, while algorithm does not provide it',
            )


class BaseThrottleSyncBackend(_BaseThrottleBackend):
    """
    Base class for all throttling backends.

    It must provide sync and async API for sync and async throttling classes.
    """

    __slots__ = ()

    @abc.abstractmethod
    def incr(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle',
        *,
        cache_key: str,
        algorithm: 'BaseThrottleAlgorithm',
    ) -> CachedRateLimit:
        """
        Sync increment cached rate limit state.

        Can be atomic, can be non atomic. Atomicity needs to be documented.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle',
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Sync get the state with no increments."""
        raise NotImplementedError


class BaseThrottleAsyncBackend(_BaseThrottleBackend):
    """
    Base class for all throttling backends.

    It must provide sync and async API for sync and async throttling classes.
    """

    __slots__ = ()

    @abc.abstractmethod
    async def incr(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'AsyncThrottle',
        *,
        cache_key: str,
        algorithm: 'BaseThrottleAlgorithm',
    ) -> CachedRateLimit:
        """Async increment cached rate limit state."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'AsyncThrottle',
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Sync get the state with no increments."""
        raise NotImplementedError
