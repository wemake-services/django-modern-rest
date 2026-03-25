import uuid

import msgspec

from dmr import Body, Controller, NewHeader, modify
from dmr.plugins.msgspec import MsgspecSerializer


class UserCreateModel(msgspec.Struct):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class UserController(  # <- `Controller` definition
    Controller[MsgspecSerializer],  # <- Passing `Serializer`
):
    @modify(headers={'X-Default': NewHeader(value='1')})  # <- extra `Metadata`
    def post(
        self,
        parsed_body: Body[UserCreateModel],
    ) -> UserModel:  # <- `Endpoint` definition
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
