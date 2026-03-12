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
    Query[QueryModel],
    Controller[MsgspecSerializer],
):
    def post(self) -> UserModel:
        return UserModel(uid=uuid.uuid4(), username='example')
