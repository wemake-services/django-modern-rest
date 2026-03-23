import dataclasses

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


@dataclasses.dataclass
class _User:
    username: str
    age: int


class UserController(Controller[MsgspecSerializer], Body[_User]):
    def put(self) -> _User:
        return self.parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn", "age": 27}}  # noqa: ERA001, E501
# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn"}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
