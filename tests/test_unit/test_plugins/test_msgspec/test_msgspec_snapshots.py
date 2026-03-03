import json
from typing import Annotated, Literal

import pytest
from django.urls import path
from syrupy.assertion import SnapshotAssertion

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)


from dmr import Body, Controller, Cookies, FileMetadata
from dmr.openapi import build_schema
from dmr.parsers import MultiPartParser
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router
from dmr.security.jwt import JWTAsyncAuth


class _UserModel(msgspec.Struct):
    age: Annotated[int, msgspec.Meta(ge=0, le=100)]
    username: Annotated[
        str,
        msgspec.Meta(extra_json_schema={'deprecated': True}),
    ]
    email: str


class _UserController(
    Controller[MsgspecSerializer],
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


class _CookieModel(msgspec.Struct):
    session_id: str
    csrf: str = msgspec.field(name='CSRF')


class _AuthedAndCookiesController(
    Controller[MsgspecSerializer],
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


class _FileModel(msgspec.Struct):
    content_type: Literal['application/json']
    size: int


class _SeveralFiles(msgspec.Struct):
    file_name1: _FileModel
    second_file: _FileModel


class _FileController(
    Controller[MsgspecSerializer],
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
