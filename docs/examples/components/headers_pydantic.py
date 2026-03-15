import pydantic

from dmr import Controller, Headers
from dmr.plugins.pydantic import PydanticSerializer


class _HeadersModel(pydantic.BaseModel):
    cache: str = pydantic.Field(alias='cache-control')
    client_id: int = pydantic.Field(alias='X-Client-Id', default=-1)


class ApiController(
    Controller[PydanticSerializer],
    Headers[_HeadersModel],
):
    def get(self) -> _HeadersModel:
        return self.parsed_headers


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "headers": {"Cache-Control": "max-age=0"}}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "headers": {"Cache-Control": "max-age=0", "X-Client-Id": "wrong"}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
