"""This counts as an integration test, because it needs real Redis database."""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

try:
    import redis
except ImportError:  # pragma: no cover
    pytest.skip(reason='redis is not installed', allow_module_level=True)

from django.core.cache import cache
from redis import asyncio as aioredis


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


@pytest.fixture
def redis_url() -> str:
    """Redis url to connect to during tests."""
    server = os.environ.get('REDIS_HOST', '127.0.0.1')
    port = os.environ.get('REDIS_PORT', '6379')
    return f'redis://{server}:{port}'


@pytest.fixture
def redis_client(
    redis_url: str,
) -> Iterator['redis.Redis[Any]']:  # pragma: no cover
    """Sync redis client."""
    try:
        with redis.Redis.from_url(redis_url) as client:
            client.flushall()

            yield client
            client.flushall()
    except redis.ConnectionError:
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')


@pytest.fixture
async def redis_async_client(  # pragma: no cover
    redis_url: str,
) -> AsyncIterator['aioredis.Redis[Any]']:
    """Async redis client."""
    try:
        async with aioredis.Redis.from_url(redis_url) as client:
            await client.flushall()

            yield client
            await client.flushall()
    except redis.ConnectionError:
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')
