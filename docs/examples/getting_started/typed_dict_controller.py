import uuid
from typing import TypedDict

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserCreateModel(TypedDict):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class UserController(Controller[MsgspecSerializer]):
    def post(self, parsed_body: Body[UserCreateModel]) -> UserModel:
        return UserModel(uid=uuid.uuid4(), email=parsed_body['email'])


# run: {"controller": "UserController", "method": "post", "url": "/api/user/", "body": {"email": "email@example.com"}}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
