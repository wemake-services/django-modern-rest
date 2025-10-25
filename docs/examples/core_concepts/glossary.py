import uuid
from typing import final

import msgspec

from django_modern_rest import Body, Controller, NewHeader, modify
from django_modern_rest.plugins.msgspec import MsgspecSerializer


class UserCreateModel(msgspec.Struct):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


@final
class UserController(  # <- `Controller` definition
    Controller[MsgspecSerializer],  # <- Passing `Serializer`
    Body[UserCreateModel],  # <- Using `Component` with a model
):
    @modify(headers={'X-Default': NewHeader(value='1')})  # <- extra `Metadata`
    def get(self) -> UserModel:  # <- `Endpoint` definition
        return UserModel(uid=uuid.uuid4(), email='default@email.com')

    def post(self) -> UserModel:  # <- `Endpoint` definition
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
