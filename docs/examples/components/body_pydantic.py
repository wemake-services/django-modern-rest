import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class _User(pydantic.BaseModel):
    username: str
    age: int


class UserController(Controller[PydanticSerializer], Body[_User]):
    def put(self) -> _User:
        return self.parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn", "age": 27}}  # noqa: ERA001, E501
# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "body": {"username": "sobolevn"}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
