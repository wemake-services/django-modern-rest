import json

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.routing import Router


class _UserModel(pydantic.BaseModel):
    email: pydantic.EmailStr
    password: pydantic.SecretStr


class _UserController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[_UserModel]) -> str:
        raise NotImplementedError


class _UserFastController(Controller[PydanticFastSerializer]):
    def post(self, parsed_body: Body[_UserModel]) -> str:
        raise NotImplementedError


def test_user_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for user controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('/user', _UserController.as_view()),
                        path('/user-fast', _UserFastController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
