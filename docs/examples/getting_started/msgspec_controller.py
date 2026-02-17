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
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        assert self.parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
