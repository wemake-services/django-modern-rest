import json
from http import HTTPStatus
from typing import Annotated, ClassVar, TypeAlias

import pydantic
from django.urls import path, re_path
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Blueprint,
    Body,
    Controller,
    Cookies,
    Path,
    Query,
    ResponseSpec,
)
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.openapi.objects import MediaTypeMetadata, ParameterMetadata
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.routing import Router, compose_blueprints
from dmr.security.jwt import JWTAsyncAuth
from tests.infra.xml_format import XmlParser, XmlRenderer


class _UserModel(pydantic.BaseModel):
    age: int = pydantic.Field(gt=0, le=100)
    username: str = pydantic.Field(deprecated=True)
    email: str

    model_config = pydantic.ConfigDict(title='CustomUserModel')


class _PathIdModel(pydantic.BaseModel):
    id: int


class _UserBlueprint(
    Blueprint[PydanticSerializer],
    Body[dict[str, int]],
):
    def post(self) -> _UserModel:
        raise NotImplementedError


class _GetUserListBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> list[_UserModel]:
        raise NotImplementedError


class _GetUserController(Controller[PydanticSerializer], Path[_PathIdModel]):
    def get(self) -> _UserModel:
        raise NotImplementedError


def test_user_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for user controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path(
                            'user/',
                            compose_blueprints(
                                _UserBlueprint,
                                _GetUserListBlueprint,
                            ).as_view(),
                        ),
                        path('user/<int:id>/', _GetUserController.as_view()),
                    ],
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
    """
    Short summary.

    And some other description text.
    """

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
                    'api/',
                    [path('cookies/', _AuthedAndCookiesController.as_view())],
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
                    'api/',
                    [path('types/', _ConditionalTypesController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


_UserModelWithExample: TypeAlias = Annotated[
    _UserModel,
    MediaTypeMetadata(example='just for test'),
]


class _ConditionalTypesWithExampleController(
    Controller[PydanticSerializer],
    Body[
        Annotated[
            _UserModel | _XmlModel,
            conditional_type({
                ContentType.json: _UserModelWithExample,
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
            ContentType.json: _UserModelWithExample,
            ContentType.xml: _XmlResponseModel,
        }),
    ]:
        raise NotImplementedError


def test_conditional_types_with_example(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [
                        path(
                            'types-with-example/',
                            _ConditionalTypesWithExampleController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _GetPostController(Controller[PydanticSerializer]):
    responses = (
        ResponseSpec(Controller.error_model, status_code=HTTPStatus.NOT_FOUND),
    )

    def get(self) -> str:
        raise NotImplementedError


def test_raw_path_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for raw path items."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path(
                            'user/<int:user_id>/post/<uuid:post_id>/',
                            _GetPostController.as_view(),
                        ),
                        re_path(
                            r'^articles/(?P<year>[0-9]{4})/(?P<slug>[\w-]+)/$',
                            _GetPostController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
