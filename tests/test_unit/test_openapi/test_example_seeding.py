from typing import Any

import pydantic
from django.conf import LazySettings
from django.urls import path

from dmr import Controller
from dmr.openapi import build_schema
from dmr.openapi.mappers.example import generate_example
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings


class _SeveralStrings(pydantic.BaseModel):
    first: str
    second: str
    third: str


class _SeedingController(Controller[PydanticSerializer]):
    def get(self) -> _SeveralStrings:
        raise NotImplementedError


def _build_schemas() -> Any:
    return build_schema(
        Router('api/v1/', [path('seeding/', _SeedingController.as_view())]),
    ).convert(skip_validation=True)['components']['schemas']


def test_examples_of_the_same_type_differ(settings: LazySettings) -> None:
    """Ensure that examples come from one stream, not from one seed."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    example = _build_schemas()['_SeveralStrings']['example']

    assert len(example) == 3
    # All three fields are `str`, they used to get the same value:
    assert len(set(example.values())) == 3


def test_examples_do_not_depend_on_previous_ones(
    settings: LazySettings,
) -> None:
    """Ensure that a schema is reproducible whatever ran before it."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}
    first_build = _build_schemas()

    # The factory is shared state, so this moves its random stream:
    for _ in range(3):
        assert generate_example(str, PydanticSerializer)

    assert _build_schemas() == first_build


def test_examples_are_disabled_by_default(settings: LazySettings) -> None:
    """Ensure that we generate nothing when there is no seed."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: None}

    assert 'example' not in _build_schemas()['_SeveralStrings']
