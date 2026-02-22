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


@pytest.mark.parametrize(
    'aiterator',
    [
        _simple_events(),
        _complex_events(),
    ],
)
def test_aiter_to_iter(aiterator: AsyncIterator[str]) -> None:
    """Ensure that iterator converter works."""
    sync = aiter_to_iter(aiterator)
    assert list(sync) == ['first', 'second']
