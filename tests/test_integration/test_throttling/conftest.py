"""This counts as an integration test, because it needs real Redis database."""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import redis
from django.core.cache import cache
from redis import asyncio as aioredis


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    # There are tests that use django-cache as well as redis:
    cache.clear()


@pytest.fixture
def redis_url() -> str:
    """Redis url to connect to during tests."""
    server = os.environ.get('REDIS_HOST', '127.0.0.1')
    port = os.environ.get('REDIS_PORT', '6379')
    # No other worker must use this redis db:
    db_number = int(os.environ.get('PYTEST_XDIST_WORKER_COUNT', '0')) + 1
    return f'redis://{server}:{port}/{db_number}'


@pytest.fixture
def redis_client(
    redis_url: str,
) -> Iterator['redis.Redis[Any]']:
    """Sync redis client."""
    try:
        with redis.Redis.from_url(redis_url) as client:
            client.flushdb()

            yield client
            client.flushdb()
    except redis.ConnectionError:  # pragma: no cover
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')


@pytest.fixture
async def redis_async_client(
    redis_url: str,
) -> AsyncIterator['aioredis.Redis[Any]']:
    """Async redis client."""
    try:
        async with aioredis.Redis.from_url(redis_url) as client:
            await client.flushdb()

            yield client
            await client.flushdb()
    except redis.ConnectionError:  # pragma: no cover
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],  # noqa: WPS110
) -> None:
    """Automatically run all throttling tests on a single worker."""
    # Otherwise, there can be parallel cache access / cache clear operations.
    for test_item in items:
        test_item.add_marker(pytest.mark.xdist_group('throttling'))
