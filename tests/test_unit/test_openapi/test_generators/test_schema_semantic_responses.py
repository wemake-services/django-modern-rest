from http import HTTPStatus
from typing import final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, modify, validate
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


@final
class _SimpleController(
    Controller[PydanticSerializer],
):
    def get(self) -> list[int]:
        raise NotImplementedError


@final
class _ModifyController(
    Controller[PydanticSerializer],
):
    @modify(status_code=HTTPStatus.CREATED)
    def post(self) -> _MyPydanticModel:
        return _MyPydanticModel(email='test@test.com')


@final
class _ValidateController(
    Controller[PydanticSerializer],
):
    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.OK,
        ),
    )
    def get(self) -> HttpResponse:
        return HttpResponse(
            b'[1, 2]',
            content_type='application/json',
        )


def test_openapi_spec_no_semantic_responses(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec should not contain auto-injected responses."""
    schema = build_schema(
        Router(
            [path('/items', _SimpleController.as_view())],
            prefix='/api',
        ),
    ).convert()

    assert schema == snapshot


def test_no_semantic_responses_modify(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec with @modify should not contain auto-injected responses."""
    schema = build_schema(
        Router(
            [path('/items', _ModifyController.as_view())],
            prefix='/api',
        ),
    ).convert()

    assert schema == snapshot


def test_no_semantic_responses_validate(
    snapshot: SnapshotAssertion,
) -> None:
    """OpenAPI spec with @validate should not have auto-injected responses."""
    schema = build_schema(
        Router(
            [path('/items', _ValidateController.as_view())],
            prefix='/api',
        ),
    ).convert()

    assert schema == snapshot
