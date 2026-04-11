import json

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, modify
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _SimpleModel(pydantic.BaseModel):
    id: int
    name: str


class _GetController(Controller[PydanticSerializer]):
    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _PostController(Controller[PydanticSerializer]):
    def post(self) -> _SimpleModel:
        raise NotImplementedError


def test_router_with_custom_config(snapshot: SnapshotAssertion) -> None:
    """Router custom config (tags, deprecated) propagates to operations."""

    class _CustomController(Controller[PydanticSerializer]):
        @modify(tags=['search'])
        def get(self) -> _SimpleModel:
            raise NotImplementedError

        @modify(deprecated=True)
        def post(self) -> _SimpleModel:
            raise NotImplementedError

    schema = build_schema(
        Router(
            'api/v1/items/',
            [path('', _CustomController.as_view())],
            tags=['items'],
            deprecated=True,
        ),
    )

    # Router tags prepended to endpoint tags
    get_op = schema.paths['/api/v1/items/'].get
    assert get_op is not None
    assert get_op.tags == ['items', 'search']
    assert get_op.deprecated is True  # router deprecated

    # Endpoint deprecated combines with router (OR logic)
    post_op = schema.paths['/api/v1/items/'].post
    assert post_op is not None
    assert post_op.tags == ['items']  # only router tags
    assert post_op.deprecated is True  # both set

    assert json.dumps(schema.convert(), indent=2) == snapshot
