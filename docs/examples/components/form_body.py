import pydantic

from dmr import Body, Controller
from dmr.parsers import FormUrlEncodedParser
from dmr.plugins.pydantic import PydanticSerializer


class _User(pydantic.BaseModel):
    username: str
    age: int


class UserController(Controller[PydanticSerializer], Body[_User]):
    parsers = (FormUrlEncodedParser(),)

    def put(self) -> _User:
        return self.parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "body": {"username": "sobolevn", "age": 27}}  # noqa: ERA001, E501
