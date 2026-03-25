import uuid

import msgspec

from dmr import Body, Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


class UserCreateModel(msgspec.Struct):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class HeaderModel(msgspec.Struct):
    consumer: str = msgspec.field(name='X-API-Consumer')


class UserController(
    Controller[MsgspecSerializer],
):
    def post(
        self,
        parsed_body: Body[UserCreateModel],
        parsed_headers: Headers[HeaderModel],
    ) -> UserModel:
        assert parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
