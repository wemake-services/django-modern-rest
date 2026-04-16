import datetime as dt
import enum
import json
from typing import Annotated, Any

import pydantic
import pytest
from django.conf import LazySettings
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.openapi.objects import Example, MediaTypeMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings


class _Status(enum.StrEnum):
    active = 'active'
    inactive = 'inactive'


class _UserModel(pydantic.BaseModel):
    age: int = pydantic.Field(gt=0, le=100)
    username: str
    status: _Status
    email: str
    salary: float
    tags: list[str]
    metadata: dict[str, str]
    created_at: dt.datetime


class _UserController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[dict[str, Any]]) -> _UserModel:
        raise NotImplementedError


@pytest.mark.freeze_time('02-11-2025 10:15:00')
def test_user_schema_with_examples(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema is correct for user controller."""
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 5,
    }

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('user/', _UserController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _WithExistingExampleModel(pydantic.BaseModel):
    field: str

    model_config = pydantic.ConfigDict(
        json_schema_extra={'example': {'field': 'example@email.com'}},
    )


class _ExistingExampleController(Controller[PydanticSerializer]):
    def post(self) -> _WithExistingExampleModel:
        raise NotImplementedError


def test_user_schema_with_existing_examples(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema is correct for existing examples controller."""
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 5,
    }

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('user/', _ExistingExampleController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _RegularBody(pydantic.BaseModel):
    coord_x: float
    coord_y: float


class _ExistingBodyExamplesController(
    Controller[PydanticSerializer],
):
    def post(
        self,
        parsed_body: Body[
            Annotated[
                _RegularBody,
                MediaTypeMetadata(
                    examples={
                        'start': Example(
                            summary='hand written example',
                            description='starting point',
                            value={'coord_x': 0, 'coord_y': 0},
                        ),
                    },
                ),
            ]
        ],
    ) -> int:
        raise NotImplementedError


def test_schema_with_body_existing_examples(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema is correct for existing examples in body."""
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 5,
    }

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('point/', _ExistingBodyExamplesController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
