"""This counts as an integration test, because it needs real Redis database."""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import redis
from django.core.cache import cache
from docker.errors import DockerException
from redis import asyncio as aioredis
from testcontainers.community.redis import AsyncRedisContainer, RedisContainer


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    # There are tests that use django-cache as well as redis:
    cache.clear()


@pytest.fixture(scope='session')
def redis_image() -> str:
    """Return the name of the image for the redis tests."""
    return os.environ.get('REDIS_IMAGE', 'redis:8-alpine')


@pytest.fixture
def redis_client(
    redis_image: str,
) -> Iterator['redis.Redis[Any]']:
    """Sync redis client."""
    try:
        with RedisContainer(redis_image) as container:
            client = container.get_client()
            with client:
                yield client
    except DockerException:  # pragma: no cover
        # `redis` can be missing in some `test-extras` envs:
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')


@pytest.fixture
async def redis_async_client(
    redis_image: str,
) -> AsyncIterator['aioredis.Redis[Any]']:
    """Async redis client."""
    try:
        with AsyncRedisContainer(redis_image) as container:
            client = await container.get_async_client()
            async with client:
                yield client
    except redis.ConnectionError:  # pragma: no cover
        # `redis` can be missing in some `test-extras` envs:
        assert os.environ.get('CI'), 'Redis can be missing only in CI'
        pytest.skip(reason='Redis server was not found')


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],  # noqa: WPS110
) -> None:
    """Automatically run all throttling tests on a single worker."""
    for test_item in items:
        # Otherwise, there can be parallel
        # cache access / cache clear operations:
        test_item.add_marker(pytest.mark.xdist_group('throttling'))
        # Otherwise, there can be flaky timeout results.
        # `func_only` is needed, because starting a redis container
        # (and possibly pulling its image) can take longer than the timeout:
        test_item.add_marker(pytest.mark.timeout(10, func_only=True))
