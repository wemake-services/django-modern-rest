from typing import Annotated

import msgspec

from dmr import Controller, Query
from dmr.openapi.objects import ParameterMetadata
from dmr.plugins.msgspec import MsgspecSerializer


class QueryModel(msgspec.Struct):
    search: str
    max_items: int


class UserController(
    Query[
        Annotated[
            QueryModel,
            ParameterMetadata(
                description='Old way to search things',
                deprecated=True,
            ),
        ]
    ],
    Controller[MsgspecSerializer],
):
    def post(self) -> str:
        return 'post'
