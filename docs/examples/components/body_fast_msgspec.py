import msgspec

from dmr import Controller
from dmr.plugins.msgspec import BodyMsgspec, MsgspecSerializer


class _User(msgspec.Struct, gc=False):
    username: str
    age: int


class UserController(Controller[MsgspecSerializer]):
    def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
        return parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn", "age": 27}}  # noqa: ERA001, E501
# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn", "age": "not-a-number"}, "curl_args": ["-D", "-"], "assert-error-text": "$.age", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
