import contextlib
import dataclasses
from collections.abc import Callable, Generator
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, assert_never

from django.http import HttpRequest, HttpResponse, HttpResponseBase

from dmr.response import infer_status_code
from dmr.test.client import DMRAsyncRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

ThrottlingWhen: TypeAlias = Literal['any', 'before_auth', 'after_auth']

_default_any_when: Final = 'any'


def assert_throttling(  # noqa: WPS210
    controller_cls: type['Controller[BaseSerializer]'],
    request_factory: Callable[[], HttpRequest],
    *,
    max_requests: int = 2,
    rate: Rate = Rate.hour,
    when: ThrottlingWhen = _default_any_when,
    success_status: HTTPStatus | None = None,
) -> tuple[HttpResponse, SyncThrottle]:
    """
    Reduce the first throttle, drive requests, and assert the ``429``.

    Sends *max_requests* allowed requests, then one that is rejected, and
    checks it with :func:`assert_throttled` -- including every header the
    reduced throttle reports. Returns the ``429`` response, so you can make
    further assertions on it.

    Parameters *when* and *rate* are passed down
    to :func:`reduced_throttling` and :func:`assert_throttled`.

    .. versionadded:: 0.12.0

    """
    view = controller_cls.as_view()
    request = request_factory()
    method: str = request.method  # type: ignore[assignment]

    with reduced_throttling(
        controller_cls,
        method=method,
        max_requests=max_requests,
        rate=rate,
        when=when,
    ) as throttle:
        assert isinstance(throttle, SyncThrottle), throttle
        for index in range(max_requests):
            _assert_ok(view(request), success_status, method)
            if index != max_requests - 1:
                # Build new request instance for new attempt:
                request = request_factory()

        throttled = _as_response(view(request_factory()))
        assert_throttled(throttled, throttle=throttle)
    return throttled, throttle  # noqa: WPS441


async def assert_async_throttling(  # noqa: WPS210
    controller_cls: type['Controller[BaseSerializer]'],
    request_factory: Callable[[], HttpRequest],
    *,
    max_requests: int = 2,
    rate: Rate = Rate.hour,
    when: ThrottlingWhen = _default_any_when,
    success_status: HTTPStatus | None = None,
) -> tuple[HttpResponse, AsyncThrottle]:
    """
    Async version of :func:`assert_throttling`.

    .. versionadded:: 0.12.0

    """
    view = controller_cls.as_view()
    request = request_factory()
    method: str = request.method  # type: ignore[assignment]
    wrap = DMRAsyncRequestFactory().wrap

    with reduced_throttling(
        controller_cls,
        method=method,
        max_requests=max_requests,
        rate=rate,
        when=when,
    ) as throttle:
        assert isinstance(throttle, AsyncThrottle), throttle
        for index in range(max_requests):
            _assert_ok(await wrap(view(request)), success_status, method)  # noqa: WPS476
            if index != max_requests - 1:
                # Build new request instance for new attempt:
                request = request_factory()

        throttled = _as_response(
            await wrap(view(request_factory())),
        )
        assert_throttled(throttled, throttle=throttle)
    return throttled, throttle  # noqa: WPS441


@contextlib.contextmanager
def reduced_throttling(
    controller_cls: type['Controller[BaseSerializer]'],
    *,
    method: HTTPMethod | str,
    max_requests: int = 2,
    rate: Rate = Rate.hour,
    when: ThrottlingWhen = _default_any_when,
) -> Generator[SyncThrottle | AsyncThrottle]:
    """
    Temporarily lower an endpoint's first throttle so a test can reach it.

    Replaces the first throttle of the chosen *when* with a copy limited to
    *max_requests*, so a few real requests trip it instead of the configured
    rate. Only the endpoint under test is affected; the original throttling is
    restored on exit. Yields the reduced throttle, whose *max_requests* tells
    you how many allowed requests to send before the next one is rejected.

    The copy also has its window widened to *rate*,
    because lowering just *max_requests* is not enough for short windows:
    a ``2/second`` throttle would reset between the driven requests and the
    endpoint would never be rejected. With an hour-long window every request
    a test sends lands inside the same window.

    Parameters:
        controller_cls: Controller whose endpoint is under test.
        method: HTTP method of the endpoint to target.
        max_requests: Limit the throttle is lowered to (``2`` by default).
            The window is always widened to one hour, see above.
        rate: Time window to narrow to
            (:attr:`~dmr.throttling.Rate.hour` by default).
        when: When to run the throttle -- ``'before_auth'``
            (checked before auth, e.g. by IP), ``'after_auth'`` (per-user,
            needs an authenticated request), or ``'any'`` (default, the first
            one checked).

    .. versionadded:: 0.12.0

    """
    endpoint = controller_cls.api_endpoints.get(str(method).upper())
    if endpoint is None:
        raise ValueError(
            f'{controller_cls.__qualname__} has no endpoint '
            f'for method {method!r}',
        )
    metadata = endpoint.metadata
    match when:
        case 'before_auth':
            throttles = metadata.throttling_before_auth
        case 'after_auth':
            throttles = metadata.throttling_after_auth
        case 'any':
            throttles = metadata.throttling
        case _:
            assert_never(when)
    if not throttles:
        raise ValueError(
            f'Endpoint {metadata.operation_id} has no throttling '
            f'to test for {when!r}',
        )

    original = throttles[0]
    reduced = original.replace(
        max_requests=max_requests,
        duration_in_seconds=rate,
    )
    # Swap the throttle in a fresh metadata; restored in `finally` below:
    endpoint.metadata = dataclasses.replace(
        metadata,
        throttling_before_auth=_swap(
            metadata.throttling_before_auth,
            original,
            reduced,
        ),
        throttling_after_auth=_swap(
            metadata.throttling_after_auth,
            original,
            reduced,
        ),
    )
    try:
        yield reduced
    finally:
        endpoint.metadata = metadata


def assert_throttled(
    response: HttpResponse,
    *,
    throttle: SyncThrottle | AsyncThrottle | None = None,
) -> None:
    """
    Assert that a response was rejected by throttling.

    Collapses the repeated ``429`` status, header and error-body checks into
    a single call:

    .. code:: python

        # Just the status + `ratelimit` error:
        assert_throttled(response)

        # Also asserts all the headers from the throttle instance exist:
        assert_throttled(response, throttle=your_throttled_instance)

    Parameters:
        response: The response to check.
        throttle: Throttle that rejected the request. When given, every header
            its providers report must be present in the response.

    *throttle* instance defines which headers are reported depends on the
    header provider's class: :class:`~dmr.throttling.headers.XRateLimit`,
    :class:`~dmr.throttling.headers.RateLimitIETFDraft`, or your own provider.

    .. versionadded:: 0.12.0

    """
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    if throttle is not None:
        _assert_reported_headers(throttle, response.headers)


def _swap(
    throttles: tuple[SyncThrottle | AsyncThrottle, ...] | None,
    old: SyncThrottle | AsyncThrottle,
    new: SyncThrottle | AsyncThrottle,
) -> tuple[SyncThrottle | AsyncThrottle, ...] | None:
    if not throttles:
        return throttles
    return tuple(new if throttle is old else throttle for throttle in throttles)


def _assert_reported_headers(
    throttle: SyncThrottle | AsyncThrottle,
    headers: Any,
) -> None:
    for provider in throttle.response_headers:
        for name in provider.provide_headers_specs():
            assert name in headers, (
                f'Header {name!r} reported by '
                f'{type(provider).__qualname__} is missing, '
                f'present headers: {dict(headers)!r}'
            )


def _as_response(candidate: HttpResponseBase) -> HttpResponse:
    assert isinstance(candidate, HttpResponse), candidate
    return candidate


def _assert_ok(
    candidate: HttpResponseBase,
    status: int | None,
    method: str,
) -> None:
    success_status = status or infer_status_code(method)
    response = _as_response(candidate)
    assert response.status_code == success_status, response.content
