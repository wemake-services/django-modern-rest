import enum
import json
from typing import Annotated, Literal

import pytest
from django.conf import LazySettings
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
from dmr.settings import Settings


class _UserModel(msgspec.Struct):
    age: Annotated[int, msgspec.Meta(ge=0, le=100)]
    username: Annotated[
        str,
        msgspec.Meta(extra_json_schema={'deprecated': True}),
    ]
    email: str


class _UserController(
    Controller[MsgspecSerializer],
):
    summary = 'Handles users'

    def post(self, parsed_body: Body[dict[str, int]]) -> _UserModel:
        raise NotImplementedError


def test_user_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for user controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/user', _UserController.as_view())],
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
):
    auth = (JWTAsyncAuth(),)

    async def get(self, parsed_cookies: Cookies[_CookieModel]) -> list[int]:
        raise NotImplementedError


def test_auth_and_cookies_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for authed and cookies controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [path('/cookies', _AuthedAndCookiesController.as_view())],
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
):
    parsers = (MultiPartParser(),)

    async def get(
        self,
        parsed_file_metadata: FileMetadata[_SeveralFiles],
    ) -> list[int]:
        raise NotImplementedError


def test_file_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [path('/file', _FileController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _Status(enum.StrEnum):
    active = 'active'
    inactive = 'inactive'


class _ExampleModel(msgspec.Struct):
    age: Annotated[int, msgspec.Meta(gt=0, le=10)]
    username: str
    status: _Status
    email: str
    salary: float
    tags: list[str]
    metadata: dict[str, str]


class _ExampleController(Controller[MsgspecSerializer]):
    def post(self) -> _ExampleModel:
        raise NotImplementedError


def test_example_schema(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema with examples is correctly generated."""
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 5,
    }

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/example', _ExampleController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
