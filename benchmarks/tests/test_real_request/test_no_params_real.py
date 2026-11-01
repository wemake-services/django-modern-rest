from __future__ import annotations

from http import HTTPStatus
from typing import Final

from pytest_codspeed import BenchmarkFixture

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRRequestFactory

_REPEAT: Final = 1000


class _NoParamsController(Controller[MsgspecSerializer]):
    def get(self) -> int:
        return 1


def test_no_params(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark through the request pipeline without any parameters."""
    request = dmr_rf.get('/test')
    controller = _NoParamsController()
    controller.setup(request)

    assert controller.dispatch(request).status_code == HTTPStatus.OK

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            controller.dispatch(request)
