from http import HTTPStatus

from django.core.cache import cache
from django.http import HttpResponse
from django.test import TestCase
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory, assert_throttled, throttle_state
from dmr.throttling import Rate, SyncThrottle

_URL = '/reports/'


class ReportsController(Controller[PydanticSerializer]):
    # A coarse hourly budget joined with a stricter per-minute limit.
    # Reaching them with real requests would need up to 1000 calls.
    throttling = (
        SyncThrottle(60, Rate.minute),
        SyncThrottle(1000, Rate.hour),
    )

    def get(self) -> str:
        return 'inside'


class TestReportsThrottling(TestCase):
    @override
    def setUp(self) -> None:
        cache.clear()  # keep throttle state isolated between tests
        self.dmr_rf = DMRRequestFactory()

    def test_endpoint_is_throttled(self) -> None:
        # Pre-fill every throttle on the endpoint to its limit in one call,
        # instead of sending hundreds of real requests in a loop:
        throttle_state(ReportsController).exhaust(self.dmr_rf.get(_URL))

        # The next request is already rejected, reporting the stricter rule:
        response = ReportsController.as_view()(self.dmr_rf.get(_URL))

        assert isinstance(response, HttpResponse)
        assert_throttled(response, limit=60)

    def test_other_clients_are_not_affected(self) -> None:
        throttle_state(ReportsController).exhaust(self.dmr_rf.get(_URL))

        # A request without a resolvable cache key is never throttled:
        request = self.dmr_rf.get(_URL)
        request.META.pop('REMOTE_ADDR', None)
        response = ReportsController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK
