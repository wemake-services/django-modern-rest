import json
from http import HTTPStatus
from typing import Annotated

import pydantic
from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller, Query, ResponseSpec, modify, validate
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import MediaTypeMetadata, ParameterMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _UserModel(pydantic.BaseModel):
    name: Annotated[
        str,
        pydantic.Field(json_schema_extra={'x-field': 'Test name'}),
    ]
    age: int


class _UserFilters(pydantic.BaseModel):
    search: str


class _UserController(Controller[PydanticSerializer]):
    # Describes the path item only, operations do not inherit it:
    x_extensions = {'x-owner': 'users-team'}

    def get(
        self,
        parsed_query: Query[
            Annotated[
                _UserFilters,
                ParameterMetadata(x_extensions={'x-searchable': True}),
            ]
        ],
    ) -> list[_UserModel]:
        raise NotImplementedError

    @modify(x_extensions={'x-rate-limit': 100})
    def post(
        self,
        parsed_body: Body[
            Annotated[
                _UserModel,
                MediaTypeMetadata(x_extensions={'x-strict': True}),
            ]
        ],
    ) -> _UserModel:
        raise NotImplementedError

    @validate(
        ResponseSpec(
            status_code=HTTPStatus.OK,
            return_type=_UserModel,
            x_extensions={'x-cacheable': True},
        ),
    )
    def put(self) -> HttpResponse:
        raise NotImplementedError

    @modify(x_extensions={})
    def delete(self) -> str:
        raise NotImplementedError


def test_x_extensions_schema(snapshot: SnapshotAssertion) -> None:
    """Each level describes its own object, nothing is inherited."""
    schema = build_schema(
        Router('api/', [path('users/', _UserController.as_view())]),
        config=OpenAPIConfig(
            title='Extended API',
            version='1.0.0',
            x_extensions={'x-tagGroups': [{'name': 'Users', 'tags': []}]},
        ),
    ).convert()

    assert json.dumps(schema, indent=2) == snapshot
