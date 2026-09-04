import pytest
from django.urls import path
from faker import Faker
from inline_snapshot import snapshot
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import (
    Components,
    Reference,
    SecurityRequirement,
    SecurityScheme,
)
from dmr.openapi.objects.schema import Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer

OpenAPIValidationError = pytest.importorskip(
    'openapi_spec_validator.validation.exceptions',
).OpenAPIValidationError


class _WrongAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> None:
        raise NotImplementedError

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {
            'wrong': SecurityScheme(
                type='http',
                name='Wrong',
            ),
        }

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return SecurityRequirement()

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        """This auth has no challenge, so this returns ``None``."""


class _UserController(Controller[PydanticSerializer]):
    @modify(auth=[_WrongAuth()])
    def post(self) -> str:
        raise NotImplementedError


def test_schema_supports_json_schema_keywords(  # noqa: WPS210
    faker: Faker,
) -> None:
    """Ensure that Schema exposes the missing JSON Schema keywords."""
    ref = f'#/components/schemas/{faker.name()}'
    anchor = faker.name()
    comment = faker.sentence()
    schema_uri = faker.url()

    schema = Schema(
        ref=ref,
        anchor=anchor,
        comment=comment,
        schema_uri=schema_uri,
    )
    router = Router('/')
    config = OpenAPIConfig(
        title='Title',
        version='0.0.1',
        components=Components(schemas={'Test': schema}),
    )
    openapi = build_schema(router, config=config).convert(skip_validation=True)

    assert openapi['components'] == snapshot({
        'schemas': {
            'Test': {
                '$ref': ref,
                '$anchor': anchor,
                '$comment': comment,
                '$schema': schema_uri,
            },
        },
    })


def test_schema_validation(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is validated correctly."""
    router = Router(
        'api/v1/',
        [path('user/', _UserController.as_view())],
    )

    with pytest.raises(OpenAPIValidationError, match='Wrong'):
        build_schema(router).convert()

    # It is possible to disable the validation:
    build_schema(router).convert(skip_validation=True)


def test_cached_schema_validation() -> None:
    """Ensure skipping validation does not bypass later validation failures."""
    schema = build_schema(
        Router(
            'api/v1/',
            [path('user/', _UserController.as_view())],
        ),
    )
    schema.convert(skip_validation=True)

    # Validate the cached schema even if the first conversion skipped it:
    with pytest.raises(OpenAPIValidationError, match='Wrong'):
        schema.convert()
