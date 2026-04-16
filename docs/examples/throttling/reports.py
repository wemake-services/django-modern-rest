from http import HTTPStatus
from typing import Final

from django.http import HttpResponse

from dmr import Controller, ResponseSpec, validate
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.throttling import AsyncThrottle, Rate, ThrottlingReport
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_draft_headers: Final = RateLimitIETFDraft()


class AsyncController(Controller[PydanticFastSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers=_draft_headers.provide_headers_specs(),
        ),
        throttling=[
            AsyncThrottle(
                1,
                Rate.second,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='per-second'),
            ),
            AsyncThrottle(
                5,
                Rate.minute,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='per-minute'),
            ),
        ],
    )
    async def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=await ThrottlingReport(self).areport(),
        )


# run: {"controller": "AsyncController", "method": "get", "url": "/api/async/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "AsyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001, E501
