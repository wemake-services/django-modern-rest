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
def _disable_semantic_responses(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.semantic_responses: False,
    }


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


def test_openapi_spec_no_semantic_responses(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec should not contain auto-injected responses."""

    class _SimpleController(Controller[PydanticSerializer]):
        def get(self) -> list[int]:
            raise NotImplementedError

    schema = build_schema(
        Router(
            [path('/items', _SimpleController.as_view())],
            prefix='/api',
        ),
    ).convert()

    assert json.dumps(schema, indent=2) == snapshot
