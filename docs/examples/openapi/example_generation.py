import uuid

import msgspec

from dmr import Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class QueryModel(msgspec.Struct):
    search: str
    max_items: int


class UserModel(msgspec.Struct):
    uid: uuid.UUID
    username: str


class UserController(
    Controller[MsgspecSerializer],
):
    def post(self, parsed_query: Query[QueryModel]) -> UserModel:
        return UserModel(uid=uuid.uuid4(), username='example')


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/", "openapi_examples_seed": 10}  # noqa: ERA001, E501
