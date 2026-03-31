import uuid
from typing import NamedTuple

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserCreateModel(NamedTuple):
    email: str


class UserModel(NamedTuple):
    email: str
    uid: uuid.UUID


class UserController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[UserCreateModel]) -> UserModel:
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
