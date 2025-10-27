import uuid
from http import HTTPStatus
from typing import final

import pydantic

from django_modern_rest import Body, Controller, NewHeader, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
):
    @modify(
        status_code=HTTPStatus.OK,
        headers={'X-Created': NewHeader(value='true')},
    )
    def post(self) -> UserModel:
        # This response would have an explicit status code `200`
        # and new explicit header `{'X-Created': 'true'}`:
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
