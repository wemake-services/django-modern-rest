from typing import ClassVar

import pydantic

from dmr import Body, Controller
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer


class _User(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('tags',))

    username: str
    tags: list[str]


class UserController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(),)

    def put(self, parsed_body: Body[_User]) -> _User:
        return parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "body": {"username": "sobolevn", "tags": ["python", "django"]}}  # noqa: ERA001, E501
# run: {"controller": "UserController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "body": {"username": "sobolevn", "tags": "single"}}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
