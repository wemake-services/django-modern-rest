import uuid

import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str
    age: int


class UserModel(UserCreateModel):
    uid: uuid.UUID


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
