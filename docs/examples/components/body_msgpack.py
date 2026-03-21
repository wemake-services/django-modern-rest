import msgspec

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgpackParser, MsgspecSerializer


class _User(msgspec.Struct):
    username: str
    age: int


class UserController(Controller[MsgspecSerializer], Body[_User]):
    parsers = (MsgpackParser(),)

    def put(self) -> _User:
        return self.parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": "examples/components/body.msgpack", "headers": {"Content-Type": "application/msgpack"}}  # noqa: ERA001, E501
# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": "examples/components/body_wrong.msgpack", "headers": {"Content-Type": "application/msgpack"}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
