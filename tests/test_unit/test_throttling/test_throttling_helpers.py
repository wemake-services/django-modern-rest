import contextlib
import copy
import sys
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import Final, Protocol

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import (
    DMRAsyncRequestFactory,
    DMRRequestFactory,
    ThrottlingLine,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import LeakyBucket
from dmr.throttling.backends import SyncDjangoCache
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import (
    RateLimitIETFDraft,
    RetryAfter,
    XRateLimit,
)
from dmr_pytest import (
    AssertAsyncThrottlingFixture,
    AssertThrottledFixture,
    AssertThrottlingFixture,
    ReducedThrottlingFixture,
)

_URL: Final = '/whatever/'

# Headers with numeric values, they accept every expectation format:
_NUMERIC_HEADERS = (
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset',
    'Retry-After',
)


class _ThrottledResponse(Protocol):
    """Type of the local `throttled_response` fixture defined below."""

    def __call__(
        self,
        controller_cls: type[Controller[PydanticFastSerializer]],
        *,
        max_requests: int = 2,
        line: ThrottlingLine = 'any',
    ) -> HttpResponse:
        """Drive a controller to its limit and return the `429`."""
        ...


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


class _PerSecondController(Controller[PydanticFastSerializer]):
    # A window this short would reset between the driven requests,
    # unless `reduced_throttling` widened it:
    throttling = (SyncThrottle(2, Rate.second),)

    def get(self) -> str:
        return 'inside'


class _IETFController(Controller[PydanticFastSerializer]):
    # Emits `RateLimit`, not `X-RateLimit-Limit`:
    throttling = (
        SyncThrottle(5, Rate.minute, response_headers=[RateLimitIETFDraft()]),
    )

    def get(self) -> str:
        return 'inside'


# Every header any of our providers reports, with the controller
# whose throttle reports it:
_REPORTED_HEADERS = (
    (_SyncController, 'X-RateLimit-Limit'),
    (_SyncController, 'X-RateLimit-Remaining'),
    (_SyncController, 'X-RateLimit-Reset'),
    (_SyncController, 'Retry-After'),
    (_IETFController, 'RateLimit'),
    (_IETFController, 'RateLimit-Policy'),
)


@pytest.fixture
def throttled_response(
    dmr_rf: DMRRequestFactory,
    dmr_reduced_throttling: ReducedThrottlingFixture,
) -> _ThrottledResponse:
    """Drive a controller to its (reduced) limit and return the `429`.

    Keyword arguments are forwarded to ``reduced_throttling``.
    """

    def factory(
        controller_cls: type[Controller[PydanticFastSerializer]],
        *,
        max_requests: int = 2,
        line: ThrottlingLine = 'any',
    ) -> HttpResponse:
        view = controller_cls.as_view()
        with dmr_reduced_throttling(
            controller_cls,
            max_requests=max_requests,
            line=line,
        ) as throttle:
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
    dmr_assert_throttled: AssertThrottledFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The endpoint is throttled after `max_requests` real requests."""
    throttled = throttled_response(_SyncController)
    # `reduced_throttling` widens the window to an hour, so the endpoint's
    # own `Rate.minute` is not what the headers report:
    dmr_assert_throttled(
        throttled,
        headers={
            'X-RateLimit-Limit': 2,
            'X-RateLimit-Reset': Rate.hour,
            'Retry-After': Rate.hour,
        },
    )


def test_reduced_throttling_widens_window(
    throttled_response: _ThrottledResponse,
    dmr_reduced_throttling: ReducedThrottlingFixture,
    dmr_assert_throttled: AssertThrottledFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Sub-minute rates are testable, because the window becomes an hour."""
    with dmr_reduced_throttling(_PerSecondController) as throttle:
        assert throttle.duration_in_seconds == Rate.hour

    rejected = throttled_response(_PerSecondController)
    dmr_assert_throttled(
        rejected,
        headers={'X-RateLimit-Limit': 2, 'X-RateLimit-Reset': Rate.hour},
    )


def test_reduced_throttling_restores(
    dmr_reduced_throttling: ReducedThrottlingFixture,
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
    dmr_reduced_throttling: ReducedThrottlingFixture,
    dmr_assert_throttled: AssertThrottledFixture,
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
    dmr_assert_throttled(throttled, headers={'X-RateLimit-Limit': 2})


def test_reduced_throttling_custom_max_requests(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`max_requests` controls how many requests are needed."""
    throttled = throttled_response(_SyncController, max_requests=1)
    dmr_assert_throttled(throttled, headers={'X-RateLimit-Limit': 1})


def test_reduced_throttling_no_throttling(
    dmr_rf: DMRRequestFactory,
    dmr_reduced_throttling: ReducedThrottlingFixture,
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
    dmr_reduced_throttling: ReducedThrottlingFixture,
) -> None:
    """Reducing a method the controller does not serve is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no endpoint'):
        stack.enter_context(
            dmr_reduced_throttling(_SyncController, method=HTTPMethod.DELETE),
        )


def test_reduced_throttling_before_auth(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`line='before_auth'` targets the before-auth throttle line."""
    rejected = throttled_response(_SyncController, line='before_auth')
    dmr_assert_throttled(rejected, headers={'X-RateLimit-Limit': 2})


def test_reduced_throttling_after_auth(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`line='after_auth'` targets the after-auth throttle line."""
    rejected = throttled_response(_AfterAuthController, line='after_auth')
    dmr_assert_throttled(rejected, headers={'X-RateLimit-Limit': 2})


def test_reduced_throttling_line_empty(
    dmr_reduced_throttling: ReducedThrottlingFixture,
) -> None:
    """Selecting a line with no throttles is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no throttling'):
        stack.enter_context(
            dmr_reduced_throttling(_SyncController, line='after_auth'),
        )


def test_assert_throttling_sync(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
) -> None:
    """The all-in-one driver reduces, drives requests, and asserts the 429."""
    response = dmr_assert_throttling(
        _SyncController,
        dmr_rf,
        _URL,
        headers={'X-RateLimit-Limit': 2},
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_assert_throttling_line(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
) -> None:
    """`line` reaches `reduced_throttling` and picks the after-auth line."""
    response = dmr_assert_throttling(
        _AfterAuthController,
        dmr_rf,
        _URL,
        line='after_auth',
        headers={'X-RateLimit-Limit': 2},
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    # The same line is empty for `_SyncController`, so it is a clear error:
    with pytest.raises(ValueError, match='no throttling'):
        dmr_assert_throttling(_SyncController, dmr_rf, _URL, line='after_auth')


def test_assert_throttling_detail_false(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
) -> None:
    """`detail=False` reaches `assert_throttled` and skips the body check."""
    response = dmr_assert_throttling(
        _SyncController,
        dmr_rf,
        _URL,
        headers={'X-RateLimit-Limit': 2},
        detail=False,
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_assert_async_throttling(
    dmr_async_rf: DMRAsyncRequestFactory,
    dmr_assert_async_throttling: AssertAsyncThrottlingFixture,
) -> None:
    """The async all-in-one driver reduces, drives requests, asserts 429."""
    response = await dmr_assert_async_throttling(
        _AsyncController,
        dmr_async_rf,
        _URL,
        line='any',
        headers={'X-RateLimit-Limit': 2},
        detail=True,
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


def test_assert_throttling_ietf_provider(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
) -> None:
    """The driver checks the headers of a non-default provider too."""
    response = dmr_assert_throttling(_IETFController, dmr_rf, _URL)
    assert 'RateLimit' in response.headers
    assert 'X-RateLimit-Limit' not in response.headers


def test_assert_throttled_provider_header_missing(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """A header the given throttle reports, but the response lacks."""
    response = throttled_response(_IETFController)
    with pytest.raises(AssertionError, match=r'XRateLimit.*missing'):
        # This throttle reports `X-RateLimit-*`, the response has `RateLimit`:
        dmr_assert_throttled(response, throttle=SyncThrottle(2, Rate.hour))


def test_throttle_response_headers() -> None:
    """Providers of a throttle are public, so helpers can reuse them."""
    default = SyncThrottle(1, Rate.hour)
    assert [type(provider) for provider in default.response_headers] == [
        XRateLimit,
        RetryAfter,
    ]

    ietf = SyncThrottle(1, Rate.hour, response_headers=[RateLimitIETFDraft()])
    assert [type(provider) for provider in ietf.response_headers] == [
        RateLimitIETFDraft,
    ]


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason='`copy.replace` is added in Python 3.13',
)
def test_throttle_copy_replace() -> None:
    """`copy.replace` works through the `__replace__` alias."""
    original = SyncThrottle(1000, Rate.minute)

    # `typeshed` wants `__replace__(**kwargs: Any)`, our alias is stricter:
    copied = copy.replace(original, max_requests=2)  # pyrefly: ignore [bad-argument-type]
    assert copied.max_requests == 2
    assert copied.duration_in_seconds == original.duration_in_seconds
    assert original.max_requests == 1000


def test_assert_throttled_rejects_ok_response(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`assert_throttled` fails on a non-throttled response."""
    response = _SyncController.as_view()(dmr_rf.get(_URL))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(AssertionError):
        dmr_assert_throttled(response)


@pytest.mark.parametrize(('controller_cls', 'header_name'), _REPORTED_HEADERS)
def test_assert_throttled_reported_headers(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
    controller_cls: type[Controller[PydanticFastSerializer]],
    header_name: str,
) -> None:
    """Every header any provider reports can be asserted by name."""
    response = throttled_response(controller_cls)
    dmr_assert_throttled(
        response,
        headers={header_name: response.headers[header_name]},
    )


@pytest.mark.parametrize('header_name', _NUMERIC_HEADERS)
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
    dmr_assert_throttled: AssertThrottledFixture,
    header_name: str,
    to_expected: Callable[[str], object],
) -> None:
    """Every header expectation accepts every documented format."""
    response = throttled_response(_SyncController)
    expected = to_expected(response.headers[header_name])
    dmr_assert_throttled(response, headers={header_name: expected})


@pytest.mark.parametrize('header_name', _NUMERIC_HEADERS)
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
    dmr_assert_throttled: AssertThrottledFixture,
    header_name: str,
    to_expected: Callable[[str], object],
) -> None:
    """A header that does not match its expectation fails clearly."""
    response = throttled_response(_SyncController)
    expected = to_expected(response.headers[header_name])
    with pytest.raises(AssertionError, match=header_name):
        dmr_assert_throttled(response, headers={header_name: expected})


def test_assert_throttled_none_expectation(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`None` is a value like any other, it never silently skips a header."""
    response = throttled_response(_SyncController)
    with pytest.raises(AssertionError, match='X-RateLimit-Limit'):
        dmr_assert_throttled(response, headers={'X-RateLimit-Limit': None})


def test_assert_throttled_missing_header(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """A missing expected header fails with a clear error, not `KeyError`."""
    response = throttled_response(_IETFController)
    with pytest.raises(AssertionError, match=r'X-RateLimit-Limit.*missing'):
        dmr_assert_throttled(response, headers={'X-RateLimit-Limit': 2})


def test_assert_throttled_detail_false(
    throttled_response: _ThrottledResponse,
    dmr_assert_throttled: AssertThrottledFixture,
) -> None:
    """`detail=False` skips the error-body check."""
    response = throttled_response(_SyncController)
    dmr_assert_throttled(response, detail=False)
