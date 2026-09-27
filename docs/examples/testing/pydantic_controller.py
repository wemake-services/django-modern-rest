import uuid

import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticFastSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str
    age: int


class UserModel(UserCreateModel):
    uid: uuid.UUID


class UserController(Controller[PydanticFastSerializer]):
    def post(self, parsed_body: Body[UserCreateModel]) -> UserModel:
        return UserModel(
            uid=uuid.uuid4(),
            age=parsed_body.age,
            email=parsed_body.email,
        )
