import uuid

import pydantic

from django_modern_rest import Body, Controller, Headers
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class HeaderModel(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        assert self.parsed_headers.token == 'secret!'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
