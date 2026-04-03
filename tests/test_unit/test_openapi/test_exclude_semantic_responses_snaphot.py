import json

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, modify
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security.jwt import JWTAsyncAuth


class _UserModel(pydantic.BaseModel):
    username: str


class _PerEndpoint(Controller[PydanticSerializer]):
    async def get(self) -> _UserModel:
        raise NotImplementedError

    @modify(exclude_semantic_responses={422})
    async def post(self) -> _UserModel:
        raise NotImplementedError


def test_exclude_per_endpoint_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that excluded semantic responses disabled per endpoint."""
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


class _PerController(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)
    exclude_semantic_responses = {422}

    async def get(self) -> _UserModel:
        raise NotImplementedError

    async def post(self) -> _UserModel:
        raise NotImplementedError


def test_exclude_per_controller_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that excluded semantic responses disabled per controller."""
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
