import json
from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any, Final

import pydantic
import pytest
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller, NewCookie, Query, ResponseSpec, validate
from dmr.errors import ErrorModel
from dmr.metadata import ResponseSpecMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle, ThrottlingReport
from dmr.throttling.algorithms import LeakyBucket
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft, RetryAfter, XRateLimit

_draft_headers: Final = RateLimitIETFDraft()
_ratelimit_headers: Final = XRateLimit()


class _ReportsController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers={
                **_draft_headers.provide_headers_specs(),
                **_ratelimit_headers.provide_headers_specs(),
            },
        ),
        throttling=[
            SyncThrottle(1, Rate.second, response_headers=[_draft_headers]),
            SyncThrottle(5, Rate.minute, response_headers=[_ratelimit_headers]),
        ],
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=ThrottlingReport(self).report(),
        )


def test_throttle_multiple_headers(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that throttle information can be served on success."""
    request = dmr_rf.get('/whatever/')

    response = _ReportsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="RemoteAddr"',
        'RateLimit': '"RemoteAddr";r=0;t=1',
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '4',
        'X-RateLimit-Reset': '60',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


class _AsyncReportsController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers={
                **_draft_headers.provide_headers_specs(),
                **_ratelimit_headers.provide_headers_specs(),
            },
        ),
        throttling=[
            AsyncThrottle(1, Rate.second, response_headers=[_draft_headers]),
            AsyncThrottle(
                5,
                Rate.minute,
                response_headers=[_ratelimit_headers],
            ),
        ],
    )
    async def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=await ThrottlingReport(self).areport(),
        )


@pytest.mark.asyncio
async def test_throttle_multiple_headers_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that throttle information can be served on success."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncReportsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="RemoteAddr"',
        'RateLimit': '"RemoteAddr";r=0;t=1',
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '4',
        'X-RateLimit-Reset': '60',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


class _MultipleThrottlesController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers=_draft_headers.provide_headers_specs(),
        ),
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='one'),
            ),
            SyncThrottle(
                5,
                Rate.minute,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='two'),
            ),
        ],
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=ThrottlingReport(self).report(),
        )


def test_throttle_multiple_throttles(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that throttle information can be served on success."""
    request = dmr_rf.get('/whatever/')

    response = _MultipleThrottlesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="one", 5;w=60;name="two"',
        'RateLimit': '"one";r=0;t=1, "two";r=4;t=60',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


class _AsyncMultipleThrottlesController(Controller[PydanticSerializer]):
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
                cache_key=RemoteAddr(name='one'),
            ),
            AsyncThrottle(
                5,
                Rate.minute,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='two'),
            ),
        ],
    )
    async def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=await ThrottlingReport(self).areport(),
        )


@pytest.mark.asyncio
async def test_throttle_multiple_throttles_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that throttle information can be served on success."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncMultipleThrottlesController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="one", 5;w=60;name="two"',
        'RateLimit': '"one";r=0;t=1, "two";r=4;t=60',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


class _QueryModel(pydantic.BaseModel):
    number: int


class _AllReportsController(Controller[PydanticSerializer]):
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
                1,
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


def test_throttle_from_errors(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle info can be served on errors."""
    # First will fail, but will consume the first ratelimit:
    request = dmr_rf.get('/whatever/?number=a')
    response = _AllReportsController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="per-second", 5;w=60;name="per-minute"',
        'RateLimit': '"per-second";r=0;t=1, "per-minute";r=4;t=60',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_query', 'number'],
                'type': 'value_error',
            },
        ],
    })

    # Next request will fail:
    request = dmr_rf.get('/whatever/?number=1')
    response = _AllReportsController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="per-second", 5;w=60;name="per-minute"',
        'RateLimit': '"per-second";r=0;t=1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })

    # Now tick a second:
    freezer.tick(delta=1)

    # Next request will be successful:
    request = dmr_rf.get('/whatever/?number=1')
    response = _AllReportsController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="per-second", 5;w=60;name="per-minute"',
        'RateLimit': '"per-second";r=0;t=1, "per-minute";r=3;t=59',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


class _NoThrottleSyncController(Controller[PydanticSerializer]):
    def get(self) -> str:
        assert ThrottlingReport(self).report() == {}
        return 'inside'


def test_no_throttle_report_sync(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that no throttle produces empty reports."""
    request = dmr_rf.get('/whatever/')

    response = _NoThrottleSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'


class _NoThrottleAsyncController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        assert await ThrottlingReport(self).areport() == {}
        return 'inside'


@pytest.mark.asyncio
async def test_no_throttle_report_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that no throttle produces empty reports."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _NoThrottleAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'


_retry_after: Final = RetryAfter()


class _AsyncLeakyBucketController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers={
                **_draft_headers.provide_headers_specs(),
                **_retry_after.provide_headers_specs(),
            },
        ),
        throttling=[
            AsyncThrottle(
                1,
                Rate.second,
                response_headers=[_draft_headers, _retry_after],
                cache_key=RemoteAddr(name='one'),
                algorithm=LeakyBucket(),
            ),
            AsyncThrottle(
                5,
                Rate.minute,
                response_headers=[_draft_headers],
                cache_key=RemoteAddr(name='two'),
                algorithm=LeakyBucket(),
            ),
        ],
    )
    async def get(self) -> HttpResponse:
        return self.to_response(
            'inside',
            headers=await ThrottlingReport(self).areport(),
        )


@pytest.mark.asyncio
async def test_leaky_bucket_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that async throttle reports are correct for leaky bucket algo."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncLeakyBucketController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="one", 5;w=60;name="two"',
        'RateLimit': '"one";r=0;t=1, "two";r=4;t=12',
        'Retry-After': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'
