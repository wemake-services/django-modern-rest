from collections.abc import Iterator
from typing import Final

import pytest
from django.core.cache import cache

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory, assert_throttling
from dmr.throttling import Rate, SyncThrottle

_URL: Final = '/reports/'


class ReportsController(Controller[PydanticSerializer]):
    # A large hourly budget: reaching it with real requests would be slow.
    throttling = (SyncThrottle(1000, Rate.hour),)

    def get(self) -> str:
        return 'inside'


@pytest.fixture(autouse=True)
def _clean_throttling_cache() -> Iterator[None]:
    cache.clear()  # keep throttle state isolated between tests
    yield
    cache.clear()


def test_endpoint_is_throttled(dmr_rf: DMRRequestFactory) -> None:
    # Lower the throttle, drive a couple of real requests, assert the 429 —
    # no 1000 requests needed. Returns the rejected response:
    assert_throttling(
        ReportsController,
        lambda: dmr_rf.get(_URL),
    )
