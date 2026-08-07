import json
from typing import Final

from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.openapi.objects import PathItem
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

_EXTERNAL_FUNC_OPENAPI: Final = PydanticSerializer.from_python(json.loads("""

"""), PathItem, strict=True)


def _external_func(request: HttpRequest) -> HttpResponse: ...


_EXTERNAL_CLASS_OPENAPI: Final = PydanticSerializer.from_python(json.loads("""

"""), PathItem, strict=True)


class _ExternalClass(View):
    def post(self, request: HttpRequest, user_id: int) -> HttpResponse: ...


class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> list[int]:
        raise NotImplementedError


def test_external_paths_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for external paths."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/async', _AsyncController.as_view())],
                    external_paths=[
                        (
                            path('/external-func', _external_func),
                            _EXTERNAL_FUNC_OPENAPI,
                        ),
                        (
                            # Parameter must be explicit
                            # in the routing's metadata:
                            path(
                                '/external-class/<int:user_id>',
                                _ExternalClass.as_view(),
                            ),
                            _EXTERNAL_CLASS_OPENAPI,
                        ),
                    ],
                    tags=['custom'],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
