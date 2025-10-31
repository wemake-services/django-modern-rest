import uuid
from typing import final

import pydantic

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str
    age: int


class UserModel(UserCreateModel):
    uid: uuid.UUID


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
):
    def post(self) -> UserModel:
        return UserModel(
            uid=uuid.uuid4(),
            age=self.parsed_body.age,
            email=self.parsed_body.email,
        )
