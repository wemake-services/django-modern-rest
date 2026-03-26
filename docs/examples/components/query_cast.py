from typing import ClassVar

import msgspec

from dmr import Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class _QueryModel(msgspec.Struct):
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('query',))

    query: str | None
    regular: str


class ApiController(Controller[MsgspecSerializer]):
    def get(self, parsed_query: Query[_QueryModel]) -> _QueryModel:
        return parsed_query


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "query": "?query=abc&regular=null"}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "query": "?query=null&regular=null"}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
