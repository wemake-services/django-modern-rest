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
    Body[UserCreateModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
