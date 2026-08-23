import json
from http import HTTPStatus
from typing import Final, cast

from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, validate
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.options_mixins import MetaMixin
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

_OPENAPI_CONFIG: Final = OpenAPIConfig(
    title='Custom Methods Test',
    version='1.0',
    openapi_version='3.2.0',
)


class _StandardController(Controller[PydanticSerializer]):
    def get(self) -> list[dict[str, str]]:
        raise NotImplementedError

    def post(self, parsed_body: dict[str, str]) -> dict[str, str]:
        raise NotImplementedError


class _MetaController(MetaMixin, Controller[PydanticSerializer]):

    def get(self) -> list[dict[str, str]]:
        raise NotImplementedError


class _PurgeController(Controller[PydanticSerializer]):
    allowed_http_methods = frozenset((
        *Controller.allowed_http_methods,
        'purge',
    ))

    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
    )
    def purge(self) -> HttpResponse:
        return cast(
            HttpResponse,
            self.to_response(None, status_code=HTTPStatus.OK),
        )


def test_standard_methods_in_path_item(snapshot: SnapshotAssertion) -> None:
    """Ensure standard methods are placed as PathItem fields."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('items/', _StandardController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


def test_meta_renders_as_options(snapshot: SnapshotAssertion) -> None:
    """Ensure meta method renders as options in the schema."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('items/', _MetaController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


def test_custom_method_in_additional_operations(
    snapshot: SnapshotAssertion,
) -> None:
    """Ensure custom HTTP methods go into additionalOperations."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('items/', _PurgeController.as_view())],
                ),
                config=_OPENAPI_CONFIG,
            ).convert(),
            indent=2,
        )
        == snapshot
    )
