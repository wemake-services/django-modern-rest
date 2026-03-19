import uuid

import msgspec

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


# Request model for POST (client sends email).
class UserCreateModel(msgspec.Struct):
    email: str


# Response model (we add uid on the server).
class UserModel(UserCreateModel):
    uid: uuid.UUID


# Controller: parses body and returns UserModel.
class UserController(
    Controller[MsgspecSerializer],
    Body[UserCreateModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
