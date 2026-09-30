from http import HTTPStatus
from typing import Annotated, ClassVar

import msgspec
from django.http import HttpResponse

from dmr import Body, Controller, Query, ResponseSpec, modify, validate
from dmr.openapi.objects import MediaTypeMetadata, ParameterMetadata
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    name: str


class UserFilters(msgspec.Struct):
    search: str


class UserController(Controller[MsgspecSerializer]):
    # Set on the path item, operations do not inherit it:
    x_extensions: ClassVar = {'x-owner': 'users-team'}

    def get(
        self,
        parsed_query: Query[
            Annotated[
                UserFilters,
                ParameterMetadata(x_extensions={'x-searchable': True}),
            ]
        ],
    ) -> list[UserModel]:
        return [UserModel(name=parsed_query.search)]

    @modify(x_extensions={'x-rate-limit': 100})  # Set on the operation
    def post(
        self,
        parsed_body: Body[
            Annotated[
                UserModel,
                MediaTypeMetadata(x_extensions={'x-strict': True}),
            ]
        ],
    ) -> UserModel:
        return parsed_body

    @validate(
        ResponseSpec(
            status_code=HTTPStatus.OK,
            return_type=UserModel,
            x_extensions={'x-cacheable': True},
        ),
    )
    def put(self) -> HttpResponse:
        return self.to_response(UserModel(name='dmr'))


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
