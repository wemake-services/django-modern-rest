from typing import ClassVar

import msgspec

from dmr import Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class _QueryModel(msgspec.Struct):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('query',))

    query: list[str]
    regular: int


class ApiController(
    Controller[MsgspecSerializer],
):
    def get(self, parsed_query: Query[_QueryModel]) -> _QueryModel:
        return parsed_query


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "query": "?query=abc&query=xyz&regular=1&regular=2"}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
