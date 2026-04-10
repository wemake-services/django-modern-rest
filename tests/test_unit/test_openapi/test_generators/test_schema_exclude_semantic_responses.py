import json
from http import HTTPStatus
from typing import final

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


@final
class _SimpleController(Controller[PydanticSerializer]):
    exclude_semantic_responses = frozenset((HTTPStatus.UNPROCESSABLE_ENTITY,))

    def get(self) -> list[int]:
        raise NotImplementedError


def test_openapi_spec_exclude_semantic_responses(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec should not contain excluded responses."""
    schema = build_schema(
        Router(
            'api/',
            [path('/items', _SimpleController.as_view())],
        ),
    ).convert()

    assert json.dumps(schema, indent=2) == snapshot
