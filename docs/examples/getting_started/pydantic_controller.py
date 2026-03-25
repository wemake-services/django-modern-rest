import uuid

import pydantic

from dmr import Body, Controller, Headers
from dmr.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class HeaderModel(pydantic.BaseModel):
    consumer: str = pydantic.Field(alias='X-API-Consumer')


class UserController(
    Controller[PydanticSerializer],
):
    def post(
        self,
        parsed_body: Body[UserCreateModel],
        parsed_headers: Headers[HeaderModel],
    ) -> UserModel:
        assert parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
