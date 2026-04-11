from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import Rate, SyncThrottle


class _XSyncThrottle(SyncThrottle):
    header_prefix = 'X-'


class SyncController(Controller[PydanticSerializer]):
    # NOTE: `0` is on purpose to show the error:
    throttling = (_XSyncThrottle(0, Rate.second),)

    def get(self) -> str:
        return 'inside'


# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: E501
# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
