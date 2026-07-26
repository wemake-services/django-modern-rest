from collections.abc import Iterator
from http import HTTPStatus
from typing import Final

import pytest
from django.core.cache import cache
from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr_pytest import (
    AssertThrottledFixture,
    AssertThrottlingFixture,
    ReducedThrottlingFixture,
)

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


def test_endpoint_is_throttled(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
) -> None:
    # Lower the throttle, drive a couple of real requests, assert the 429 —
    # no 1000 requests needed. Returns the rejected response:
    response = dmr_assert_throttling(
        ReportsController,
        dmr_rf,
        _URL,
        headers={'X-RateLimit-Limit': 2},
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_endpoint_is_throttled_manually(
    dmr_rf: DMRRequestFactory,
    dmr_reduced_throttling: ReducedThrottlingFixture,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    # Finer control: drive the requests yourself through the reduced
    # throttle, then check the rejected response with `assert_throttled`.
    view = ReportsController.as_view()
    with dmr_reduced_throttling(ReportsController) as throttle:
        for _ in range(throttle.max_requests):
            allowed = view(dmr_rf.get(_URL))
            assert allowed.status_code == HTTPStatus.OK

        rejected = view(dmr_rf.get(_URL))
        assert isinstance(rejected, HttpResponse)
        dmr_assert_throttled(
            rejected,
            throttle=throttle,  # every header it reports must be there
            headers={'X-RateLimit-Limit': 2},
        )
