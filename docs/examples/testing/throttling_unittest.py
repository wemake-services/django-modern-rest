from typing import Final

from django.core.cache import cache
from django.test import TestCase
from typing_extensions import override

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


# In your test files:
class TestReportsThrottling(TestCase):
    @override
    def setUp(self) -> None:
        cache.clear()  # keep throttle state isolated between tests
        self.dmr_rf = DMRRequestFactory()

    def test_endpoint_is_throttled(self) -> None:
        # Lower the throttle, drive a couple of real requests, assert the 429 —
        # no 1000 requests needed. Returns the rejected response:
        assert_throttling(
            ReportsController,
            lambda: self.dmr_rf.get(_URL),
        )
