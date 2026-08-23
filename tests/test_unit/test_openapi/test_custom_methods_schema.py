"""Tests for custom HTTP methods in OpenAPI schema generation."""
import json

from django.urls import path

from dmr import Controller
from dmr.openapi import build_schema
from dmr.options_mixins import MetaMixin
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _StandardController(Controller[PydanticSerializer]):
    """A controller with standard HTTP methods only."""

    def get(self) -> list[dict[str, str]]:
        raise NotImplementedError

    def post(self, parsed_body: dict[str, str]) -> dict[str, str]:
        raise NotImplementedError


class _MetaController(MetaMixin, Controller[PydanticSerializer]):
    """A controller with meta method (generates OPTIONS)."""

    def get(self) -> list[dict[str, str]]:
        raise NotImplementedError


class _DeleteController(Controller[PydanticSerializer]):
    """A controller with only DELETE method."""

    def delete(self) -> None:
        raise NotImplementedError


def _build_schema(controller_cls: type) -> dict:
    """Build OpenAPI schema for a controller."""
    return build_schema(
        Router('api/v1/', [path('items/', controller_cls.as_view())]),
    ).convert()


def test_standard_methods_in_path_item() -> None:
    """Ensure standard methods are placed as PathItem fields."""
    schema = json.loads(json.dumps(_build_schema(_StandardController)))
    items = schema['paths']['/api/v1/items/']

    assert 'get' in items
    assert 'post' in items
    assert 'additionalOperations' not in items


def test_meta_generates_options_in_schema() -> None:
    """Ensure meta method generates OPTIONS in the schema."""
    schema = json.loads(json.dumps(_build_schema(_MetaController)))
    items = schema['paths']['/api/v1/items/']

    assert 'options' in items
    assert items['options']['operationId'].startswith('options')


def test_allowed_http_methods_controls_endpoints() -> None:
    """Ensure only methods in allowed_http_methods appear in schema."""
    schema = json.loads(json.dumps(_build_schema(_DeleteController)))
    items = schema['paths']['/api/v1/items/']

    assert 'delete' in items
    assert 'get' not in items
    assert 'post' not in items


def test_no_additional_operations_for_standard_only() -> None:
    """Ensure additionalOperations is absent when only standard methods used."""
    schema = json.loads(json.dumps(_build_schema(_StandardController)))
    items = schema['paths']['/api/v1/items/']

    assert 'additionalOperations' not in items
