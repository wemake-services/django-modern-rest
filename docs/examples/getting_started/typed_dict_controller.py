import uuid
from typing import TypedDict

from dmr import Body, Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


class UserCreateModel(TypedDict):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


HeaderModel = TypedDict('HeaderModel', {'X-API-Consumer': str})


class UserController(
    Controller[MsgspecSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types."""
        assert self.parsed_headers['X-API-Consumer'] == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body['email'])
