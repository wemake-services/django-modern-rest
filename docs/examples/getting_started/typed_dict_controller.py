import uuid
from typing import TypedDict

from dmr import Body, Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


class UserCreateModel(TypedDict):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


HeaderModel = TypedDict('HeaderModel', {'X-API-Consumer': str})


class UserController(Controller[MsgspecSerializer]):
    def post(
        self,
        parsed_body: Body[UserCreateModel],
        parsed_headers: Headers[HeaderModel],
    ) -> UserModel:
        assert parsed_headers['X-API-Consumer'] == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=parsed_body['email'])
