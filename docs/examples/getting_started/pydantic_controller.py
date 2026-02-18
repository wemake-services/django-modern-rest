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
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        assert self.parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
