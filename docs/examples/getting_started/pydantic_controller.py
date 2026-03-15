import uuid

import pydantic

from dmr import Body, Controller, Headers
from dmr.plugins.pydantic import PydanticSerializer


# Request model for POST (client sends email).
class UserCreateModel(pydantic.BaseModel):
    email: str


# Response model (we add uid on the server).
class UserModel(UserCreateModel):
    uid: uuid.UUID


# Parsed from X-API-Consumer request header.
class HeaderModel(pydantic.BaseModel):
    consumer: str = pydantic.Field(alias='X-API-Consumer')


# Controller: parses body and headers, returns UserModel.
class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        assert self.parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
