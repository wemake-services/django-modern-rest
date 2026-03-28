import pydantic

from dmr import Controller, Cookies
from dmr.plugins.pydantic import PydanticSerializer


class _CookiesModel(pydantic.BaseModel):
    cache: str
    client_id: int


class ApiController(Controller[PydanticSerializer]):
    def get(self, parsed_cookies: Cookies[_CookiesModel]) -> _CookiesModel:
        return parsed_cookies


# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "cookies": {"cache": "yes", "client_id": "1"}}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "url": "/api/users/", "method": "get", "cookies": {"cache": "yes", "client_id": "wrong"}, "curl_args": ["-D", "-"], "assert-error-text": "client_id", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
