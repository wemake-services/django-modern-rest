from collections.abc import AsyncIterator

from dmr.streaming.jsonl import Json


# Correct:
async def valid_events() -> AsyncIterator[Json]:
    yield 1
    yield 5.0
    yield 'a'
    yield True
    yield None
    yield []
    yield [1, 2, 'a', {'a': 1}]
    yield {'key': {'nested': [1, None]}}


async def wrong_events() -> AsyncIterator[Json]:
    yield object()  # type: ignore[misc]
    yield 1j  # type: ignore[misc]
    yield b''  # type: ignore[misc]
    yield [b'']  # type: ignore[list-item]
    yield {1: 2}  # type: ignore[dict-item]
