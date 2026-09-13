from __future__ import annotations

import threading
from typing import Final

from pytest_codspeed import BenchmarkFixture

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle

_REPEAT: Final = 1000


class _ThrottleController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return 'ok'


def test_sync_throttle_allowed(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark an allowed throttle check with the local cache backend."""
    # Keep the benchmark on the successful path across all CodSpeed iterations.
    throttle = SyncThrottle(1_000_000_000, Rate.minute)
    endpoint = _ThrottleController.api_endpoints['GET']
    controller = _ThrottleController()
    controller.setup(
        dmr_rf.get('/test', REMOTE_ADDR='192.0.2.1'),
    )
    lock = threading.Lock()

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            throttle(endpoint, controller, lock)
