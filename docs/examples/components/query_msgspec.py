import msgspec

from dmr import Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class _QueryModel(msgspec.Struct):
    query: str
    count: int


class ApiController(Controller[MsgspecSerializer]):
    def get(self, parsed_query: Query[_QueryModel]) -> _QueryModel:
        return parsed_query


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "query": "?query=abc&count=10"}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "query": "?query=abc", "curl_args": ["-D", "-"], "assert-error-text": "count", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
