from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import HeaderJWTAsyncAuth


class APIController(Controller[PydanticSerializer]):
    auth = (HeaderJWTAsyncAuth(),)

    async def get(self) -> str:
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "assert-error-text": "Not authenticated", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
