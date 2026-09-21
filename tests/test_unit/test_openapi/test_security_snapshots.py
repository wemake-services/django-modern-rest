import json
from http import HTTPStatus

from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import Components, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security.jwt import HeaderJWTSyncAuth


class _SecurityController(Controller[PydanticSerializer]):
    security = [{'gateway': []}]

    @modify(security=[{'mesh': []}])
    def get(self) -> str:
        raise NotImplementedError

    @validate(
        ResponseSpec(return_type=str, status_code=HTTPStatus.CREATED),
        auth=[HeaderJWTSyncAuth()],
        security=[{'mesh': []}],
    )
    def post(self) -> HttpResponse:
        raise NotImplementedError

    @modify(security=None)
    def put(self) -> str:
        raise NotImplementedError


class _UndeclaredSecurityController(Controller[PydanticSerializer]):
    @modify(security=[{'undeclared': []}])
    def get(self) -> str:
        raise NotImplementedError


def test_undeclared_security_scheme() -> None:
    """Undeclared schemes are the user's responsibility, we don't check them."""
    schema = build_schema(
        Router(
            'api/v1/',
            [path('undeclared/', _UndeclaredSecurityController.as_view())],
        ),
    )

    converted = schema.convert()

    assert converted['paths']['/api/v1/undeclared/']['get']['security'] == [
        {'undeclared': []},
    ]
    assert 'securitySchemes' not in converted['components']


def test_user_security_schema(snapshot: SnapshotAssertion) -> None:
    """User provided `security` is merged with `auth` requirements."""
    config = OpenAPIConfig(
        title='Security API',
        version='1.0.0',
        security=[{'jwt': []}],
        components=Components(
            security_schemes={
                'gateway': SecurityScheme(
                    type='apiKey',
                    name='X-Gateway-Key',
                    security_scheme_in='header',
                ),
                'mesh': SecurityScheme(
                    type='mutualTLS',
                    description='Service mesh mTLS',
                ),
            },
        ),
    )
    router = Router(
        'api/v1/',
        [path('security/', _SecurityController.as_view())],
    )

    schema = build_schema(router, config=config)

    assert json.dumps(schema.convert(), indent=2) == snapshot
