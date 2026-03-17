import json

import pydantic
from django.urls import path, re_path
from syrupy.assertion import SnapshotAssertion

from dmr import Blueprint, Controller, modify
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, compose_blueprints
from dmr.security.jwt import JWTAsyncAuth


class _UserModel(pydantic.BaseModel):
    username: str


class _PerEndpoint(Controller[PydanticSerializer]):
    async def get(self) -> _UserModel:
        raise NotImplementedError

    @modify(semantic_responses=False)
    async def post(self) -> _UserModel:
        raise NotImplementedError


def test_per_endpoint_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is semantic for disabled per blueprint."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [path('per_endpoint/', _PerEndpoint.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _PerBlurprint(Blueprint[PydanticSerializer]):
    semantic_responses = False

    async def get(self) -> _UserModel:
        raise NotImplementedError

    async def post(self) -> _UserModel:
        raise NotImplementedError


def test_per_blueprint_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is semantic for disabled per blueprint."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'per_blueprint/<str:kwarg_id>',
                            compose_blueprints(_PerBlurprint).as_view(),
                        ),
                        re_path(
                            r'^articles/(?P<other>[0-9]{4})/(?P<kwarg_id>[\w-]+)/$',
                            compose_blueprints(_PerBlurprint).as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _PerController(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)
    semantic_responses = False

    async def get(self) -> _UserModel:
        raise NotImplementedError

    async def post(self) -> _UserModel:
        raise NotImplementedError


def test_per_controller_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is semantic for disabled per controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [path('per_controller/', _PerController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
