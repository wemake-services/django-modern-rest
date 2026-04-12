from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.headers import RateLimitIETFDraft


class SyncController(Controller[PydanticSerializer]):
    throttling = (
        SyncThrottle(1, Rate.minute, response_headers=[RateLimitIETFDraft()]),
    )

    def get(self) -> str:
        return 'inside'


# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/"}  # noqa: ERA001
# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
