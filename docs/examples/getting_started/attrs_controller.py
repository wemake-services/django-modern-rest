import uuid

import attrs

from dmr import Body, Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


@attrs.define
class UserCreateModel:
    email: str


@attrs.define
class UserModel(UserCreateModel):
    uid: uuid.UUID


@attrs.define
class HeaderModel:
    consumer: str = attrs.field(alias='X-API-Consumer')


class UserController(
    Controller[MsgspecSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        assert self.parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
