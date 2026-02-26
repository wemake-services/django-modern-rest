import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import closing
from typing import TYPE_CHECKING, TypeVar

_ItemT = TypeVar('_ItemT')


if TYPE_CHECKING:

    def identity(wrapped: _ItemT) -> _ItemT:
        """We still need to lie in type annotations. I am sad."""
        raise NotImplementedError

else:

    async def identity(wrapped: _ItemT) -> _ItemT:
        """
        Just returns an object wrapped in a coroutine.

        Needed for django view handling, where async views
        require coroutine return types.
        """
        return wrapped


def aiter_to_iter(aiterator: AsyncIterator[_ItemT]) -> Iterator[_ItemT]:
    """
    Convert async iterator to a sync one.

    This implementation has a lot of potential limitations.
    And should not be used anywhere.
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
        try:
            aclose = aiterator.aclose  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover
            pass  # noqa: WPS420
        else:
            loop.run_until_complete(aclose())  # pyright: ignore[reportUnknownArgumentType]
