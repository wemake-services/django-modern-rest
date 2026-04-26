from typing import Any

import redis
from django.core.cache import caches

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.backends.redis import SyncRedis

# If `CACHES['redis']` with `django.core.cache.backends.redis.RedisCache`
# backend is defined in `settings.py`:
redis_client: 'redis.Redis[Any]' = caches['redis']._cache.get_client()  # type: ignore[attr-defined]  # noqa: SLF001


class SyncController(Controller[PydanticSerializer]):
    throttling = (
        SyncThrottle(
            max_requests=1,
            duration_in_seconds=Rate.minute,
            backend=SyncRedis(redis_client),
        ),
    )

    def get(self) -> str:
        return 'inside'
