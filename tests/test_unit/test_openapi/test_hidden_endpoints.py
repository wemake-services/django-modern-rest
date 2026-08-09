import json
from http import HTTPStatus

import pydantic
from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Body,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _UserModel(pydantic.BaseModel):
    email: str


class _FullyHiddenController(Controller[PydanticSerializer]):
    ignore_from_spec = True

    def post(self, parsed_body: Body[_UserModel]) -> dict[str, str]:
        raise NotImplementedError

    def get(self) -> list[_UserModel]:
        raise NotImplementedError

    @modify(description='Put')
    def put(self) -> str:
        raise NotImplementedError

    @validate(ResponseSpec(str, status_code=HTTPStatus.OK), description='Patch')
    def patch(self) -> HttpResponse:
        raise NotImplementedError


def test_fully_hidden_controller(snapshot: SnapshotAssertion) -> None:
    """Ensure that it is possible to fully hide a controller from the spec."""
    for endpoint in _FullyHiddenController.api_endpoints.values():
        assert endpoint.metadata.ignore_from_spec, endpoint.metadata.method

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/hidden/',
                    [
                        path('fully/', _FullyHiddenController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _PartiallyHiddenController(Controller[PydanticSerializer]):
    ignore_from_spec = True

    # Will be hidden:

    def post(self, parsed_body: Body[_UserModel]) -> dict[str, str]:
        raise NotImplementedError

    def get(self) -> list[_UserModel]:
        raise NotImplementedError

    # Won't be hidden:

    @modify(description='Put', ignore_from_spec=False)
    def put(self) -> str:
        raise NotImplementedError

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        description='Patch',
        ignore_from_spec=False,
    )
    def patch(self) -> HttpResponse:
        raise NotImplementedError


def test_partially_hidden_controller(snapshot: SnapshotAssertion) -> None:
    """Ensure that it is possible to hide some endpoints from the spec."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/hidden/',
                    [
                        path(
                            'partially/',
                            _PartiallyHiddenController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _PartiallyHiddenEndpoints(Controller[PydanticSerializer]):
    # Won't be hidden:

    def post(self, parsed_body: Body[_UserModel]) -> dict[str, str]:
        raise NotImplementedError

    def get(self) -> list[_UserModel]:
        raise NotImplementedError

    # Will be hidden:

    @modify(ignore_from_spec=True)
    def put(self) -> str:
        raise NotImplementedError

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        ignore_from_spec=True,
    )
    def patch(self) -> HttpResponse:
        raise NotImplementedError


def test_partially_hidden_endpoints(snapshot: SnapshotAssertion) -> None:
    """Ensure that it is possible to hide some endpoints from the spec."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/hidden/',
                    [
                        path('endpoints/', _PartiallyHiddenEndpoints.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
