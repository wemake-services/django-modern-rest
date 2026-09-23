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
from dmr.types import EMPTY


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
    """Controller tags are applied to all endpoints without own tags."""
    assert _TaggedController.api_endpoints['GET'].metadata.tags == ['users']
    assert _TaggedController.api_endpoints['POST'].metadata.tags == ['admin']
    assert _TaggedController.api_endpoints['PUT'].metadata.tags == ['admin']


def test_controller_tags_schema(snapshot: SnapshotAssertion) -> None:
    """Endpoint tags override controller tags, which override router ones."""
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
    assert _UntaggedController.api_endpoints['GET'].metadata.tags is EMPTY
    assert _UntaggedController.api_endpoints['POST'].metadata.tags == ['admin']


class _ExplicitTags(Controller[PydanticSerializer]):
    tags = ('users',)

    @modify(tags=[*tags, 'admin'])
    def get(self) -> _SimpleModel:
        raise NotImplementedError

    @modify(tags=None)
    def post(self) -> _SimpleModel:
        raise NotImplementedError


def test_explicit_tags() -> None:
    """Tags can be merged explicitly or disabled with `None`."""
    assert _ExplicitTags.api_endpoints['GET'].metadata.tags == [
        'users',
        'admin',
    ]
    assert _ExplicitTags.api_endpoints['POST'].metadata.tags is None


def test_none_tags_schema(snapshot: SnapshotAssertion) -> None:
    """Router tags are not applied when endpoint tags are `None`."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/users/',
                    [path('', _ExplicitTags.as_view())],
                    tags=['v1'],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _SubTaggedController(_TaggedController):
    tags = ('admins',)


def test_subclass_controller_tags() -> None:
    """Subclasses can redefine tags of the base controller."""
    assert _SubTaggedController.api_endpoints['GET'].metadata.tags == ['admins']
    assert _SubTaggedController.api_endpoints['POST'].metadata.tags == ['admin']
