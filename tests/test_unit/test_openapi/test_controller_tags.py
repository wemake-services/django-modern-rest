import json
from http import HTTPStatus

import pydantic
from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _SimpleModel(pydantic.BaseModel):
    id: int
    name: str


class _TaggedController(Controller[PydanticSerializer]):
    tags = ('users',)

    def get(self) -> _SimpleModel:
        raise NotImplementedError

    @modify(tags=['admin'])
    def post(self) -> _SimpleModel:
        raise NotImplementedError

    @validate(
        ResponseSpec(_SimpleModel, status_code=HTTPStatus.OK),
        tags=['admin'],
    )
    def put(self) -> HttpResponse:
        raise NotImplementedError


def test_controller_tags() -> None:
    """Controller tags are applied to all endpoints of this controller."""
    assert _TaggedController.api_endpoints['GET'].metadata.tags == ['users']
    assert _TaggedController.api_endpoints['POST'].metadata.tags == [
        'users',
        'admin',
    ]
    assert _TaggedController.api_endpoints['PUT'].metadata.tags == [
        'users',
        'admin',
    ]


def test_controller_tags_schema(snapshot: SnapshotAssertion) -> None:
    """Router, controller, and endpoint tags are merged in this order."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/users/',
                    [path('', _TaggedController.as_view())],
                    tags=['v1'],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _UntaggedController(Controller[PydanticSerializer]):
    def get(self) -> _SimpleModel:
        raise NotImplementedError

    @modify(tags=['admin'])
    def post(self) -> _SimpleModel:
        raise NotImplementedError


def test_no_controller_tags() -> None:
    """Endpoint tags are not affected when a controller has no tags."""
    assert _UntaggedController.api_endpoints['GET'].metadata.tags is None
    assert _UntaggedController.api_endpoints['POST'].metadata.tags == ['admin']


class _SubTaggedController(_TaggedController):
    tags = ('admins',)


def test_subclass_controller_tags() -> None:
    """Subclasses can redefine tags of the base controller."""
    assert _SubTaggedController.api_endpoints['GET'].metadata.tags == ['admins']
    assert _SubTaggedController.api_endpoints['POST'].metadata.tags == [
        'admins',
        'admin',
    ]
