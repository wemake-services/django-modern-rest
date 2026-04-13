from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import AsyncThrottle, Rate
from dmr.throttling.headers import XRateLimit


class AsyncController(Controller[PydanticSerializer]):
    throttling = (
        AsyncThrottle(1, Rate.minute, response_headers=[XRateLimit()]),
    )

    async def get(self) -> str:
        return 'inside'


# run: {"controller": "AsyncController", "method": "get", "url": "/api/async/"}  # noqa: ERA001
# run: {"controller": "AsyncController", "method": "get", "url": "/api/async/", "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "AsyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001, E501
