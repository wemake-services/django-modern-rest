import json
from typing import Annotated, Literal, final

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Body,
    Controller,
    Cookies,
    FileMetadata,
    Headers,
    Path,
    Query,
)
from dmr.openapi import build_schema
from dmr.openapi.objects import ParameterMetadata
from dmr.parsers import JsonParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


@final
class _Model(pydantic.BaseModel):
    name: str
    age: int = 0


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _FileModel(pydantic.BaseModel):
    name: str


@final
class _DefaultsController(Controller[PydanticSerializer]):
    parsers = (JsonParser(), MultiPartParser())

    def post(  # noqa: WPS211
        self,
        parsed_body: Body[_Model | None] = None,
        parsed_query: Query[
            Annotated[_Model | None, ParameterMetadata(description='Query')]
        ] = None,
        parsed_headers: Headers[_Model | None] = None,
        parsed_cookies: Cookies[_Model | None] = None,
        parsed_path: Path[_PathModel | None] = None,
        parsed_file_metadata: FileMetadata[_FileModel | None] = None,
    ) -> str:
        raise NotImplementedError


@final
class _RequiredBodyController(Controller[PydanticSerializer]):
    parsers = (JsonParser(), MultiPartParser())

    def post(
        self,
        parsed_body: Body[_Model],
        parsed_file_metadata: FileMetadata[_FileModel | None] = None,
    ) -> str:
        raise NotImplementedError


def test_component_defaults_schema(snapshot: SnapshotAssertion) -> None:
    """Ensures that components with defaults are optional in the schema."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [
                        path(
                            'defaults/<int:user_id>/',
                            _DefaultsController.as_view(),
                        ),
                        path('required/', _RequiredBodyController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


@final
class _OtherModel(pydantic.BaseModel):
    name: str
    other: str
    age: int = 0


@final
class _UnionDefaultsController(Controller[PydanticSerializer]):
    def post(  # noqa: WPS211
        self,
        parsed_body: Body[_Model | dict[str, str] | int] = 0,
        parsed_query: Query[_Model | Literal['']] = '',
        parsed_headers: Headers[_Model | _OtherModel | None] = None,
        parsed_cookies: Cookies[dict[str, str] | None] = None,
    ) -> str:
        raise NotImplementedError


@final
class _UnionRequiredController(Controller[PydanticSerializer]):
    # NOTE: OpenAPI support for `Union` in `headers` and `query` is rather
    # bad, so we can't really do much, except just not using unions :(
    def get(
        self,
        parsed_query: Query[_Model | _OtherModel],
        parsed_headers: Headers[_Model | None],
    ) -> str:
        raise NotImplementedError


def test_union_defaults_schema(snapshot: SnapshotAssertion) -> None:
    """Ensures that unions with non-model members produce parameters."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [
                        path('unions/', _UnionDefaultsController.as_view()),
                        path('required/', _UnionRequiredController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
