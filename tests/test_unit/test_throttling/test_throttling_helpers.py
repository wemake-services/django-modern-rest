import contextlib
from collections.abc import Awaitable, Callable
from http import HTTPMethod, HTTPStatus
from typing import Final, TypeAlias

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import LeakyBucket
from dmr.throttling.backends import SyncDjangoCache
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_URL: Final = '/whatever/'

# Each `assert_throttled` header kwarg and the response header it checks:
_HEADERS = (
    ('limit', 'X-RateLimit-Limit'),
    ('reset', 'X-RateLimit-Reset'),
    ('retry_after', 'Retry-After'),
)

# Types of the `dmr.test` helpers as provided by their pytest fixtures:
_ReducedThrottling: TypeAlias = Callable[
    ...,
    contextlib.AbstractContextManager[SyncThrottle | AsyncThrottle],
]
_AssertThrottled: TypeAlias = Callable[..., None]
_AssertThrottling: TypeAlias = Callable[..., HttpResponse]
_AssertAsyncThrottling: TypeAlias = Callable[..., Awaitable[HttpResponse]]
_ThrottledResponse: TypeAlias = Callable[..., HttpResponse]


class _SyncController(Controller[PydanticFastSerializer]):
    throttling = (
        SyncThrottle(5, Rate.minute),
        SyncThrottle(10, Rate.hour),
    )

    def get(self) -> str:
        return 'inside'

    @modify(throttling=None)
    def put(self) -> str:
        return 'inside'


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = (AsyncThrottle(3, Rate.hour),)

    async def get(self) -> str:
        return 'inside'


class _AfterAuthController(Controller[PydanticFastSerializer]):
    # `runs_before_auth=False` puts this throttle in the after-auth line,
    # while its `REMOTE_ADDR` key still resolves for anonymous requests.
    throttling = (
        SyncThrottle(
            5,
            Rate.minute,
            cache_key=RemoteAddr(runs_before_auth=False),
        ),
    )

    def get(self) -> str:
        return 'inside'


class _IETFController(Controller[PydanticFastSerializer]):
    # Emits `RateLimit`, not `X-RateLimit-Limit`:
    throttling = (
        SyncThrottle(5, Rate.minute, response_headers=[RateLimitIETFDraft()]),
    )

    def get(self) -> str:
        return 'inside'


@pytest.fixture
def throttled_response(
    dmr_rf: DMRRequestFactory,
    dmr_reduced_throttling: _ReducedThrottling,
) -> _ThrottledResponse:
    """Drive a controller to its (reduced) limit and return the `429`.

    Extra keyword arguments (``max_requests``, ``line``, ...) are forwarded
    to ``reduced_throttling``.
    """

    def factory(
        controller_cls: type[Controller[PydanticFastSerializer]],
        **kwargs: object,
    ) -> HttpResponse:
        view = controller_cls.as_view()
        with dmr_reduced_throttling(controller_cls, **kwargs) as throttle:
            for _ in range(throttle.max_requests):
                ok = view(dmr_rf.get(_URL))
                assert isinstance(ok, HttpResponse)
                assert ok.status_code == HTTPStatus.OK, ok.content
            throttled = view(dmr_rf.get(_URL))
        assert isinstance(throttled, HttpResponse)
        return throttled

    return factory


def test_reduced_throttling_sync(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The endpoint is throttled after `max_requests` real requests."""
    throttled = throttled_response(_SyncController)
    dmr_assert_throttled(
        throttled,
        limit=2,
        reset=Rate.minute,
        retry_after=Rate.minute,
    )


def test_reduced_throttling_restores(
    dmr_reduced_throttling: _ReducedThrottling,
) -> None:
    """The endpoint's throttling is left untouched after the block."""
    endpoint = _SyncController.api_endpoints['GET']
    before = endpoint.metadata.throttling
    assert before is not None
    assert before[0].max_requests == 5

    with dmr_reduced_throttling(_SyncController):
        assert endpoint.metadata.throttling is not None
        assert endpoint.metadata.throttling[0].max_requests == 2

    assert endpoint.metadata.throttling is before
    assert endpoint.metadata.throttling[0].max_requests == 5


@pytest.mark.asyncio
async def test_reduced_throttling_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    dmr_reduced_throttling: _ReducedThrottling,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`reduced_throttling` works for async controllers too."""
    view = _AsyncController.as_view()
    with dmr_reduced_throttling(_AsyncController) as throttle:
        for _ in range(throttle.max_requests):
            ok = await dmr_async_rf.wrap(view(dmr_async_rf.get(_URL)))
            assert isinstance(ok, HttpResponse)
            assert ok.status_code == HTTPStatus.OK, ok.content
        throttled = await dmr_async_rf.wrap(view(dmr_async_rf.get(_URL)))

    assert isinstance(throttled, HttpResponse)
    dmr_assert_throttled(throttled, limit=2)


def test_reduced_throttling_custom_max_requests(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`max_requests` controls how many requests are needed."""
    throttled = throttled_response(_SyncController, max_requests=1)
    dmr_assert_throttled(throttled, limit=1)


def test_reduced_throttling_no_throttling(
    dmr_rf: DMRRequestFactory,
    dmr_reduced_throttling: _ReducedThrottling,
) -> None:
    """Reducing an endpoint without throttling is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no throttling'):
        stack.enter_context(
            dmr_reduced_throttling(_SyncController, method=HTTPMethod.PUT),
        )

    # The `put` endpoint itself works fine (covers the handler):
    allowed = _SyncController.as_view()(dmr_rf.put(_URL))
    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.OK


def test_reduced_throttling_unknown_method(
    dmr_reduced_throttling: _ReducedThrottling,
) -> None:
    """Reducing a method the controller does not serve is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no endpoint'):
        stack.enter_context(
            dmr_reduced_throttling(_SyncController, method=HTTPMethod.DELETE),
        )


def test_reduced_throttling_before_auth(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`line='before_auth'` targets the before-auth throttle line."""
    rejected = throttled_response(_SyncController, line='before_auth')
    dmr_assert_throttled(rejected, limit=2)


def test_reduced_throttling_after_auth(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`line='after_auth'` targets the after-auth throttle line."""
    rejected = throttled_response(_AfterAuthController, line='after_auth')
    dmr_assert_throttled(rejected, limit=2)


def test_reduced_throttling_line_empty(
    dmr_reduced_throttling: _ReducedThrottling,
) -> None:
    """Selecting a line with no throttles is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no throttling'):
        stack.enter_context(
            dmr_reduced_throttling(_SyncController, line='after_auth'),
        )


def test_assert_throttling_sync(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: _AssertThrottling,
) -> None:
    """The all-in-one driver reduces, drives requests, and asserts the 429."""
    response = dmr_assert_throttling(_SyncController, dmr_rf, _URL, limit=2)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_assert_async_throttling(
    dmr_async_rf: DMRAsyncRequestFactory,
    dmr_assert_async_throttling: _AssertAsyncThrottling,
) -> None:
    """The async all-in-one driver reduces, drives requests, asserts 429."""
    response = await dmr_assert_async_throttling(
        _AsyncController,
        dmr_async_rf,
        _URL,
        limit=2,
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_throttle_replace() -> None:
    """`replace` overrides the given fields and keeps the rest."""
    original = SyncThrottle(1000, Rate.minute)

    # Override just `max_requests`; everything else is preserved:
    reduced = original.replace(max_requests=2)
    assert reduced.max_requests == 2
    assert original.max_requests == 1000  # original untouched
    assert reduced.duration_in_seconds == original.duration_in_seconds
    assert reduced.cache_key is original.cache_key

    # No arguments -> an equivalent copy:
    copied = original.replace()
    assert copied.max_requests == 1000
    assert copied.duration_in_seconds == original.duration_in_seconds

    # Override every field:
    other = original.replace(
        max_requests=7,
        duration_in_seconds=Rate.hour,
        cache_key=RemoteAddr(runs_before_auth=False),
        backend=SyncDjangoCache(),
        algorithm=LeakyBucket(),
        response_headers=[RateLimitIETFDraft()],
    )
    assert other.max_requests == 7
    assert other.duration_in_seconds == Rate.hour
    assert other.cache_key.runs_before_auth is False


def test_assert_throttled_rejects_ok_response(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`assert_throttled` fails on a non-throttled response."""
    response = _SyncController.as_view()(dmr_rf.get(_URL))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(AssertionError):
        dmr_assert_throttled(response)


@pytest.mark.parametrize(('kwarg', 'header_name'), _HEADERS)
@pytest.mark.parametrize(
    'to_expected',
    [
        int,  # `int`, matched as its string form
        str,  # `str`, matched as-is
        lambda _actual: IsStr(regex=r'\d+'),  # any matcher object
    ],
)
def test_assert_throttled_header_formats(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
    kwarg: str,
    header_name: str,
    to_expected: Callable[[str], object],
) -> None:
    """Every header assertion accepts every documented format."""
    response = throttled_response(_SyncController)
    expected = to_expected(response.headers[header_name])
    dmr_assert_throttled(
        response,
        limit=expected if kwarg == 'limit' else None,
        reset=expected if kwarg == 'reset' else None,
        retry_after=expected if kwarg == 'retry_after' else None,
    )


@pytest.mark.parametrize(('kwarg', 'header_name'), _HEADERS)
@pytest.mark.parametrize(
    'to_expected',
    [
        lambda actual: int(actual) + 1,  # wrong `int`
        lambda actual: str(int(actual) + 1),  # wrong `str`
        lambda _actual: IsStr(regex=r'[a-z]+'),  # matcher that cannot match
    ],
)
def test_assert_throttled_header_mismatch(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
    kwarg: str,
    header_name: str,
    to_expected: Callable[[str], object],
) -> None:
    """A header that does not match its expectation fails clearly."""
    response = throttled_response(_SyncController)
    expected = to_expected(response.headers[header_name])
    with pytest.raises(AssertionError, match=header_name):
        dmr_assert_throttled(
            response,
            limit=expected if kwarg == 'limit' else None,
            reset=expected if kwarg == 'reset' else None,
            retry_after=expected if kwarg == 'retry_after' else None,
        )


def test_assert_throttled_missing_header(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """A missing expected header fails with a clear error, not `KeyError`."""
    response = throttled_response(_IETFController)
    with pytest.raises(AssertionError, match=r'X-RateLimit-Limit.*missing'):
        dmr_assert_throttled(response, limit=2)


def test_assert_throttled_detail_false(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: _AssertThrottled,
) -> None:
    """`detail=False` skips the error-body check."""
    response = throttled_response(_SyncController)
    dmr_assert_throttled(response, detail=False)
