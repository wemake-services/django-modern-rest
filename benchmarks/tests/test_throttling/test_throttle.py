from __future__ import annotations

from typing import Final, Self

from pytest_codspeed import BenchmarkFixture
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr

_REPEAT: Final = 1000


class _Auth(SyncAuth):
    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self:
        return self

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        return None


class _ThrottleController(Controller[MsgspecSerializer]):
    auth = (_Auth(),)
    throttling = (
        SyncThrottle(1_000_000_000, Rate.minute),
        SyncThrottle(
            1_000_000_000,
            Rate.minute,
            cache_key=RemoteAddr(
                runs_before_auth=False,
                name='AfterAuth',
            ),
        ),
    )

    def get(self) -> None:
        return None


def test_sync_throttle_allowed(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark auth and throttling through dispatch."""
    request = dmr_rf.get('/test', REMOTE_ADDR='192.0.2.1')
    controller = _ThrottleController()
    controller.setup(request)

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            controller.dispatch(request)
