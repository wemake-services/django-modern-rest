import dataclasses
import uuid

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


@dataclasses.dataclass
class UserCreateModel:
    email: str


@dataclasses.dataclass
class UserModel(UserCreateModel):
    uid: uuid.UUID


class UserController(
    Controller[MsgspecSerializer],
    # Dataclasses do not support field name aliases, so can't use Headers :(
):
    def post(self, parsed_body: Body[UserCreateModel]) -> UserModel:
        return UserModel(uid=uuid.uuid4(), email=parsed_body.email)
