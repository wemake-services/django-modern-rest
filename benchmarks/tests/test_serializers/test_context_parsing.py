from __future__ import annotations

from typing import Any, Final

import pytest
from pytest_codspeed import BenchmarkFixture
from typing_extensions import TypedDict

from dmr import Body, Controller, Headers, Query
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory

_BODY: Final = b'{"email": "user@example.com", "age": 27}'


class _User(TypedDict):
    email: str
    age: int


class _Query(TypedDict):
    page: int


def _build_controller(
    serializer: type[BaseSerializer],
    *,
    with_defaults: bool,
) -> type[Controller[Any]]:
    if with_defaults:

        class _DefaultsController(Controller[serializer]):  # type: ignore[valid-type]
            def post(
                self,
                parsed_body: Body[_User | None] = None,
                parsed_query: Query[_Query | None] = None,
                parsed_headers: Headers[dict[str, str] | None] = None,
            ) -> int:
                return 1

        return _DefaultsController

    class _RequiredController(Controller[serializer]):  # type: ignore[valid-type]
        def post(
            self,
            parsed_body: Body[_User],
            parsed_query: Query[_Query],
            parsed_headers: Headers[dict[str, str]],
        ) -> int:
            return parsed_query['page']

    return _RequiredController


@pytest.mark.parametrize('serializer', [PydanticSerializer, MsgspecSerializer])
@pytest.mark.parametrize('with_defaults', [False, True])
def test_context_parsing(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
    serializer: type[BaseSerializer],
    *,
    with_defaults: bool,
) -> None:
    """Benchmark parsing of all components at once."""
    request = dmr_rf.post(
        '/test?page=2',
        data=_BODY,
        content_type='application/json',
        headers={'X-API-Token': 'token'},
    )
    controller_cls = _build_controller(serializer, with_defaults=with_defaults)
    endpoint = controller_cls.api_endpoints['POST']
    context = endpoint._serializer_context  # noqa: SLF001
    controller = controller_cls()
    controller.setup(request)

    @benchmark
    def factory() -> dict[str, Any]:
        return context(endpoint, controller)
