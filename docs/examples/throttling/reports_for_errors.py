from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any, Final

import pydantic
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, NewCookie, Query, ResponseSpec, validate
from dmr.errors import ErrorModel
from dmr.metadata import ResponseSpecMetadata
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.renderers import Renderer
from dmr.throttling import Rate, SyncThrottle, ThrottlingReport
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_draft_headers: Final = RateLimitIETFDraft()


class _QueryModel(pydantic.BaseModel):
    number: int


class SyncController(Controller[PydanticFastSerializer]):
    error_model = Annotated[
        ErrorModel,
        ResponseSpecMetadata(headers=_draft_headers.provide_headers_specs()),
    ]

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers=_draft_headers.provide_headers_specs(),
        ),
        throttling=[
            SyncThrottle(
                2,
                Rate.second,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='per-second'),
            ),
            SyncThrottle(
                5,
                Rate.minute,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='per-minute'),
            ),
        ],
    )
    def get(self, parsed_query: Query[_QueryModel]) -> HttpResponse:
        return self.to_response('inside')

    @override
    def to_response(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        response_headers = ThrottlingReport(self).report()
        response_headers.update(headers or {})
        return super().to_response(
            raw_data,
            status_code=status_code,
            headers=response_headers,
            cookies=cookies,
            renderer=renderer,
        )


# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", "query": "?number=1", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "SyncController", "method": "get", "url": "/api/sync/", "query": "?number=a", "curl_args": ["-D", "-"], "assert-error-text": "to parse string", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
