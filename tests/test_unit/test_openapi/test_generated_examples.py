from typing import Any

import pytest
from django.conf import LazySettings
from django.urls import path

from dmr import Body, Controller
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings


class _UserController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[dict[str, Any]]) -> str:
        raise NotImplementedError


def _build_schema(openapi_version: str) -> dict[str, Any]:
    return build_schema(
        Router('api/v1/', [path('user/', _UserController.as_view())]),
        config=OpenAPIConfig(
            title='Examples',
            version='1.0.0',
            openapi_version=openapi_version,
        ),
    ).convert()


def _inline_body_schema(dumped: dict[str, Any]) -> Any:
    """Inline schemas go through the generated schema code path."""
    operation = dumped['paths']['/api/v1/user/']['post']
    return operation['requestBody']['content']['application/json']['schema']


def _referenced_schema(dumped: dict[str, Any]) -> Any:
    """Registered components go through the reference code path."""
    return dumped['components']['schemas']['ErrorModel']


@pytest.mark.parametrize(
    'find_schema',
    [_inline_body_schema, _referenced_schema],
)
def test_generated_example_before_v32(
    find_schema: Any,
    settings: LazySettings,
) -> None:
    """Ensure that older versions still use the OAS ``example`` keyword."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = find_schema(_build_schema('3.1.0'))

    assert schema['example']
    assert 'examples' not in schema


@pytest.mark.parametrize(
    'find_schema',
    [_inline_body_schema, _referenced_schema],
)
def test_generated_example_since_v32(
    find_schema: Any,
    settings: LazySettings,
) -> None:
    """Ensure that 3.2 uses JSON Schema ``examples``, not ``example``."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = find_schema(_build_schema('3.2.0'))

    assert 'example' not in schema
    assert schema['examples'] == [
        find_schema(_build_schema('3.1.0'))['example'],
    ]


def test_disabled_examples_write_nothing(settings: LazySettings) -> None:
    """Ensure that we don't write ``examples: [null]`` when disabled."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: None}

    schema = _inline_body_schema(_build_schema('3.2.0'))

    assert 'example' not in schema
    assert 'examples' not in schema
