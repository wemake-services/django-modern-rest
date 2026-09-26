import asyncio
from collections.abc import AsyncIterator

import pytest

from dmr.internal.io import aiter_to_iter


async def _simple_events() -> AsyncIterator[str]:
    yield 'first'
    yield 'second'


async def _complex_events() -> AsyncIterator[str]:
    yield 'first'
    await asyncio.sleep(0.1)
    yield 'second'
    # We need to test explicit `return` here:
    return  # noqa: WPS324


class _NonClosableEvents:
    """Minimal async iterator which has no ``aclose`` method."""

    def __init__(self) -> None:
        self._events = iter(('first', 'second'))

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.mark.parametrize(
    'aiterator',
    [
        _simple_events(),
        _complex_events(),
        _NonClosableEvents(),
    ],
)
def test_aiter_to_iter(
    *,
    aiterator: AsyncIterator[str],
) -> None:
    """Ensure that iterator converter works."""
    sync = aiter_to_iter(aiter(aiterator))
    assert list(sync) == ['first', 'second']
