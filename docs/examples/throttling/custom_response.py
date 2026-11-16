from http import HTTPStatus

from dmr import Controller, ResponseSpec, modify
from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.headers import RetryAfter

retry_after_header = RetryAfter()


class SyncController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[
            SyncThrottle(1, Rate.minute, response_headers=[retry_after_header]),
        ],
        exclude_semantic_responses={HTTPStatus.TOO_MANY_REQUESTS},
        extra_responses=[
            ResponseSpec(
                ErrorModel,
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
                headers=retry_after_header.provide_headers_specs(),
                description='Custom ratelimit response',
            ),
        ],
    )
    def get(self) -> str:
        return 'inside'


# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/"}  # noqa: ERA001
# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: E501, ERA001
# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
