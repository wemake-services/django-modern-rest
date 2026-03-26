from typing import ClassVar

import msgspec

from dmr import Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


class _HeadersModel(msgspec.Struct):
    __dmr_split_commas__: ClassVar[frozenset[str]] = frozenset(('x-tag',))

    tags: list[int] = msgspec.field(name='X-Tag')


class UserController(Controller[MsgspecSerializer]):
    def get(self, parsed_headers: Headers[_HeadersModel]) -> _HeadersModel:
        return parsed_headers


# run: {"controller": "UserController", "url": "/api/users/", "method": "get", "headers": [["X-Tag", "1"], ["X-Tag", "2"]]}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
