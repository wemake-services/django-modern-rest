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
):
    def post(
        self,
        parsed_body: Body[UserCreateModel],
        parsed_headers: Headers[HeaderModel],
    ) -> UserModel:
        assert parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
