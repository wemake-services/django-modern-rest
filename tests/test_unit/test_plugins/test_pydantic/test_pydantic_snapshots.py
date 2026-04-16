import json
import uuid
from typing import Any, Generic, TypeVar

import pydantic
from django.urls import path
from pydantic_extra_types import Color
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.routing import Router


class _UserModel(pydantic.BaseModel):
    email: pydantic.EmailStr
    password: pydantic.SecretStr
    preferred_color: Color


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


class _UserProfile(pydantic.BaseModel):
    age: int


class _UserInputData(pydantic.BaseModel):
    email: str
    profile: _UserProfile


class _UserOutputData(_UserInputData):
    uid: uuid.UUID


_ModelT = TypeVar('_ModelT')


class _UserDocument(pydantic.BaseModel, Generic[_ModelT]):
    user: _ModelT

    @classmethod
    @override
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:  # noqa: WPS110
        return (
            super()
            .model_parametrized_name(params)
            .replace('[', '_')
            .replace(']', '_')
        )


class _GenericController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_body: Body[_UserDocument[_UserInputData]],
    ) -> _UserDocument[_UserOutputData]:
        raise NotImplementedError


def test_generic_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for generic controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('/generic', _GenericController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
