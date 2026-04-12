from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import Rate, SyncThrottle


class SyncController(Controller[PydanticSerializer]):
    throttling = (SyncThrottle(5, Rate.hour),)

    @modify(throttling=[SyncThrottle(1, Rate.minute)])
    def get(self) -> str:
        return 'inside'


# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/"}  # noqa: ERA001
# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: E501, ERA001
# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
