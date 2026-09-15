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


@pytest.mark.parametrize('openapi_version', ['3.1.0', '3.2.0'])
@pytest.mark.parametrize(
    'find_schema',
    [_inline_body_schema, _referenced_schema],
)
def test_generated_examples_keyword(
    settings: LazySettings,
    *,
    find_schema: Callable[[dict[str, Any]], Schema | Reference],
    openapi_version: str,
) -> None:
    """Ensure that generated examples always use JSON Schema ``examples``."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = find_schema(_build_schema(openapi_version))

    assert schema['examples']
    assert 'example' not in schema


def test_disabled_examples_write_nothing(settings: LazySettings) -> None:
    """Ensure that we don't write ``examples: [null]`` when disabled."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: None}

    schema = _inline_body_schema(_build_schema('3.2.0'))

    assert 'example' not in schema
    assert 'examples' not in schema
