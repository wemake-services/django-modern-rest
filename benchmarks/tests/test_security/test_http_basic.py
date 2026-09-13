from __future__ import annotations

from typing import Final, Self

from pytest_codspeed import BenchmarkFixture
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.http import HttpBasicSyncAuth, basic_auth
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory

_REPEAT: Final = 1000


class _BasicAuth(HttpBasicSyncAuth):
    __slots__ = ()

    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if username == 'benchmark' and password == 'secret':
            return self
        return None


class _AuthController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return 'ok'


def test_http_basic_auth_success(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark extraction and validation of valid Basic credentials."""
    auth = _BasicAuth()
    endpoint = _AuthController.api_endpoints['GET']
    controller = _AuthController()
    controller.setup(
        dmr_rf.get(
            '/test',
            headers={
                'Authorization': basic_auth('benchmark', 'secret'),
            },
        ),
    )

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            assert auth(endpoint, controller) is auth
