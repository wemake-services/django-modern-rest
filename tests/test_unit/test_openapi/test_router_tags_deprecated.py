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


def test_router_with_custom_config(snapshot: SnapshotAssertion) -> None:
    """Router custom config (tags, deprecated) propagates to operations."""

    class _CustomController(Controller[PydanticSerializer]):
        @modify(tags=['search'], deprecated=False)
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

    assert json.dumps(schema.convert(), indent=2) == snapshot
