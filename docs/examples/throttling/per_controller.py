from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import AsyncThrottle, Rate


class AsyncController(Controller[PydanticSerializer]):
    throttling = (AsyncThrottle(1, Rate.minute),)

    async def get(self) -> str:
        return 'inside'


# run: {"controller": "AsyncController", "method": "get", "url": "/api/sync/"}  # noqa: ERA001
# run: {"controller": "AsyncController", "method": "get", "url": "/api/sync/", "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: E501, ERA001
# openapi: {"controller": "AsyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001, E501
