import json
from typing import Literal

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller, Cookies, FileMetadata
from dmr.openapi import build_schema
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security.jwt import JWTAsyncAuth


class _UserModel(pydantic.BaseModel):
    age: int = pydantic.Field(gt=0, le=100)
    username: str = pydantic.Field(deprecated=True)
    email: str

    model_config = pydantic.ConfigDict(title='CustomUserModel')


class _UserController(
    Controller[PydanticSerializer],
    Body[dict[str, int]],
):
    def post(self) -> _UserModel:
        raise NotImplementedError


def test_user_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for user controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/user', _UserController.as_view())],
                    prefix='/api/v1',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _CookieModel(pydantic.BaseModel):
    session_id: str
    csrf: str = pydantic.Field(alias='CSRF')


class _AuthedAndCookiesController(
    Controller[PydanticSerializer],
    Cookies[_CookieModel],
):
    auth = (JWTAsyncAuth(),)

    async def get(self) -> list[int]:
        raise NotImplementedError


def test_auth_and_cookies_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for authed and cookies controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/cookies', _AuthedAndCookiesController.as_view())],
                    prefix='/api',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _FileModel(pydantic.BaseModel):
    content_type: Literal['application/json']
    size: int


class _SeveralFiles(pydantic.BaseModel):
    file_name1: _FileModel
    second_file: _FileModel


class _FileController(
    Controller[PydanticSerializer],
    FileMetadata[_SeveralFiles],
):
    parsers = (MultiPartParser(),)

    async def get(self) -> list[int]:
        raise NotImplementedError


def test_file_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/file', _FileController.as_view())],
                    prefix='/',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _BodyAndFileController(
    Controller[PydanticSerializer],
    Body[_UserModel],
    FileMetadata[_SeveralFiles],
):
    parsers = (MultiPartParser(),)

    async def post(self) -> list[int]:
        raise NotImplementedError


def test_body_and_file_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/file', _BodyAndFileController.as_view())],
                    prefix='/',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
