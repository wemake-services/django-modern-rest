from typing import Annotated

import msgspec

from dmr import Controller, Query
from dmr.openapi.objects import ParameterMetadata
from dmr.plugins.msgspec import MsgspecSerializer


class QueryModel(msgspec.Struct):
    search: str
    max_items: int


class UserController(
    Controller[MsgspecSerializer],
):
    def post(
        self,
        parsed_query: Query[
            Annotated[
                QueryModel,
                ParameterMetadata(
                    description='Old way to search things',
                    deprecated=True,
                ),
            ]
        ],
    ) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
