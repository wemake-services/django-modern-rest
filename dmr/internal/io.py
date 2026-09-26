import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Iterator
from contextlib import aclosing, closing, nullcontext
from typing import TYPE_CHECKING, Any, Protocol, TypeGuard, TypeVar

_ItemT = TypeVar('_ItemT')


class _SupportsAclose(Protocol):
    """An object that can be asynchronously closed."""

    def aclose(self) -> Awaitable[Any]: ...


def _supports_aclose(
    potentially_closable: object,
) -> TypeGuard[_SupportsAclose]:
    """Return whether *potentially_closable* provides an async close method."""
    return callable(getattr(potentially_closable, 'aclose', None))


if TYPE_CHECKING:

    def identity(wrapped: _ItemT) -> _ItemT:
        """We still need to lie in type annotations. I am sad."""
        raise NotImplementedError

else:

    async def identity(wrapped: _ItemT) -> _ItemT:
        """
        Just returns an object wrapped in a coroutine.

        Needed for Django view handling, where async views
        require coroutine return types.
        """
        return wrapped


def aiter_to_iter(aiterator: AsyncIterator[_ItemT]) -> Iterator[_ItemT]:
    """
    Convert async iterator to a sync one.

    This implementation has a lot of potential limitations
    and should not be used anywhere.
    We use it for ``runserver`` integration with SSE.
    """
    with closing(asyncio.new_event_loop()) as loop:
        while True:
            try:
                yield loop.run_until_complete(anext(aiterator))
            except (StopAsyncIteration, asyncio.CancelledError):
                break

        # After we received an exception, we want to explicitly close any
        # async generators.
        if _supports_aclose(aiterator):
            loop.run_until_complete(aiterator.aclose())


def maybe_aclosing(
    streaming_content: AsyncIterable[Any],
) -> aclosing[Any] | nullcontext[Any]:
    """Close the async iterator if it supports closing."""
    # We want to close any async generators after they are fully used.
    # Why? Because they can be cancelled at any point
    # and not do any cleanup.
    return (
        aclosing(streaming_content)
        if _supports_aclose(streaming_content)
        else nullcontext()
    )
