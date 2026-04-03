import json
from typing import final

import pydantic
import pytest
from django.conf import LazySettings
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings


@pytest.fixture(autouse=True)
def _exclude_semantic_responses(
    settings: LazySettings,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.exclude_semantic_responses: frozenset((422,)),
    }


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


def test_openapi_spec_exclude_semantic_responses(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec should not contain excluded responses."""

    class _SimpleController(Controller[PydanticSerializer]):
        def get(self) -> list[int]:
            raise NotImplementedError

    schema = build_schema(
        Router(
            'api/',
            [path('/items', _SimpleController.as_view())],
        ),
    ).convert()

    assert json.dumps(schema, indent=2) == snapshot
