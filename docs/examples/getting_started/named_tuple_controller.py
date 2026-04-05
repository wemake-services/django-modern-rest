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
    # Dataclasses do not support field name aliases, so can't use Headers :(
):
    def post(self, parsed_body: Body[UserCreateModel]) -> UserModel:
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
