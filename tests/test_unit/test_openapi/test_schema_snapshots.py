import json
from http import HTTPStatus
from typing import Annotated, ClassVar, Literal

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Body,
    Controller,
    Cookies,
    FileMetadata,
    Query,
    ResponseSpec,
    modify,
)
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.openapi.objects import ParameterMetadata
from dmr.parsers import JsonParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.routing import Router
from dmr.security.jwt import JWTAsyncAuth
from tests.infra.xml_format import XmlParser, XmlRenderer


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
    csrf: str = pydantic.Field(alias='CSRF', description='Override')


class _QueryModel(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('tags',))
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('query',))

    tags: list[str]
    query: str | None
    regular: int


class _AuthedAndCookiesController(
    Controller[PydanticSerializer],
    Cookies[
        Annotated[
            _CookieModel,
            ParameterMetadata(description='Cookies metadata'),
        ]
    ],
    Query[
        Annotated[
            _QueryModel,
            ParameterMetadata(style='deepObject', explode=True),
        ]
    ],
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
    """Model docs."""

    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('attachments',))

    attachments: list[_FileModel]
    second_file: _FileModel


# TODO: test file response
class _FileController(
    Controller[PydanticSerializer],
    FileMetadata[_SeveralFiles],
):
    parsers = (MultiPartParser(),)

    @modify(operation_id='file_test_id', deprecated=True)
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


class _DescriptionModel(pydantic.BaseModel):
    """Description from doc."""

    first: str
    second: list[int]


class _BodyAndFileController(
    Controller[PydanticSerializer],
    Body[_DescriptionModel],
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


class _XmlModel(pydantic.BaseModel):
    xml_value: int


class _XmlResponseModel(pydantic.BaseModel):
    xml_response: str


class _ConditionalTypesController(
    Controller[PydanticSerializer],
    Body[
        Annotated[
            _UserModel | _XmlModel,
            conditional_type({
                ContentType.json: _UserModel,
                ContentType.xml: _XmlModel,
            }),
        ],
    ],
):
    responses = (
        ResponseSpec(
            str,
            status_code=HTTPStatus.CONFLICT,
            limit_to_content_types={
                ContentType.json,
            },
        ),
    )
    parsers = [JsonParser(), XmlParser()]
    renderers = [JsonRenderer(), XmlRenderer()]

    def post(
        self,
    ) -> Annotated[
        _UserModel | _XmlResponseModel,
        'comment',
        conditional_type({
            ContentType.json: _UserModel,
            ContentType.xml: _XmlResponseModel,
        }),
    ]:
        raise NotImplementedError


def test_conditional_types(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/types', _ConditionalTypesController.as_view())],
                    prefix='/api',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
