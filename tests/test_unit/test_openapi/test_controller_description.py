import json
from typing import Any

import pydantic
import pytest
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _SimpleModel(pydantic.BaseModel):
    id: int
    name: str


class _DocstringController(Controller[PydanticSerializer]):
    """Summary from docstring.

    Description from docstring.
    """

    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _OnlySummaryDocstringController(Controller[PydanticSerializer]):
    """Only summary from docstring."""

    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _NoDocstringController(Controller[PydanticSerializer]):
    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _ExplicitController(Controller[PydanticSerializer]):
    """Summary from docstring.

    Description from docstring.
    """

    summary = 'Summary from attribute.'
    description = 'Description from attribute.'

    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _NoSummaryController(Controller[PydanticSerializer]):
    """Summary from docstring.

    Description from docstring.
    """

    summary = None

    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _NoDescriptionController(Controller[PydanticSerializer]):
    """Summary from docstring.

    Description from docstring.
    """

    description = None

    def get(self) -> _SimpleModel:
        raise NotImplementedError


class _SubclassController(_DocstringController):
    def post(self) -> _SimpleModel:
        raise NotImplementedError


def _build_path_item(
    controller: type[Controller[PydanticSerializer]],
) -> dict[str, Any]:
    schema = build_schema(
        Router('api/', [path('users/', controller.as_view())]),
    ).convert()
    path_item: dict[str, Any] = schema['paths']['/api/users/']
    return path_item


@pytest.mark.parametrize(
    ('controller', 'expected_summary', 'expected_description'),
    [
        (
            _DocstringController,
            'Summary from docstring.',
            'Description from docstring.',
        ),
        (
            _OnlySummaryDocstringController,
            'Only summary from docstring.',
            None,
        ),
        (
            _NoDocstringController,
            None,
            None,
        ),
        (
            _ExplicitController,
            'Summary from attribute.',
            'Description from attribute.',
        ),
        (
            _NoSummaryController,
            None,
            'Description from docstring.',
        ),
        (
            _NoDescriptionController,
            'Summary from docstring.',
            None,
        ),
        (
            _SubclassController,
            None,
            None,
        ),
    ],
)
def test_controller_description(
    *,
    controller: type[Controller[PydanticSerializer]],
    expected_summary: str | None,
    expected_description: str | None,
) -> None:
    """Path item docs are parsed from docstrings unless set explicitly."""
    path_item = _build_path_item(controller)

    assert path_item.get('summary') == expected_summary
    assert path_item.get('description') == expected_description


def test_controller_description_schema(snapshot: SnapshotAssertion) -> None:
    """Controller docstring ends up in the resulting OpenAPI schema."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/users/',
                    [path('', _DocstringController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
