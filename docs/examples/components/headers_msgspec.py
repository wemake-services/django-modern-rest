import msgspec

from dmr import Controller, Headers
from dmr.plugins.msgspec import MsgspecSerializer


class _HeadersModel(msgspec.Struct):
    cache: str = msgspec.field(name='cache-control')
    client_id: int = msgspec.field(name='X-Client-Id', default=-1)


class ApiController(Controller[MsgspecSerializer]):
    def get(self, parsed_headers: Headers[_HeadersModel]) -> _HeadersModel:
        return parsed_headers


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "headers": {"Cache-Control": "max-age=0"}}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "headers": {"Cache-Control": "max-age=0", "X-Client-Id": "wrong"}, "curl_args": ["-D", "-"], "assert-error-text": "X-Client-Id", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
