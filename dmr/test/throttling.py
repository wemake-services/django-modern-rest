import contextlib
import dataclasses
from collections.abc import Generator, Mapping
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from django.http import HttpResponse, HttpResponseBase

from dmr.internal.json import json_loads
from dmr.test.client import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

HeaderValue: TypeAlias = object
"""
Expected value for a header checked by :func:`assert_throttled`.

An ``int`` (rendered to its ``str`` form), a ``str``, or a matcher
like ``dirty_equals.IsStr``.

Typed as :class:`object`, because the header is compared with ``==``,
so no narrower static type is correct -- matchers like ``IsStr``
are deliberately unhashable, so a ``Protocol`` won't help.

.. versionadded:: 0.12.0
"""

ThrottlingLine: TypeAlias = Literal['any', 'before_auth', 'after_auth']
"""
Throttle line to target.

Either ``'before_auth'`` (checked before auth, e.g. by IP),
``'after_auth'`` (per-user, needs an authenticated request),
or ``'any'`` (the first one checked).

.. versionadded:: 0.12.0
"""


@contextlib.contextmanager
def reduced_throttling(
    controller_cls: 'type[Controller[BaseSerializer]]',
    *,
    method: HTTPMethod = HTTPMethod.GET,
    max_requests: int = 2,
    line: ThrottlingLine = 'any',
) -> Generator[SyncThrottle | AsyncThrottle, None, None]:
    """
    Temporarily lower an endpoint's first throttle so a test can reach it.

    Replaces the first throttle of the chosen ``line`` with a copy limited to
    ``max_requests``, so a few real requests trip it instead of the configured
    rate. Only the endpoint under test is affected; the original throttling is
    restored on exit. Yields the reduced throttle, whose ``max_requests`` tells
    you how many allowed requests to send before the next one is rejected.

    The copy also has its window widened to :attr:`~dmr.throttling.Rate.hour`,
    because lowering just ``max_requests`` is not enough for short windows:
    a ``2/second`` throttle would reset between the driven requests and the
    endpoint would never be rejected. With an hour-long window every request
    a test sends lands inside the same window.

    Parameters:
        controller_cls: Controller whose endpoint is under test.
        method: HTTP method of the endpoint to target.
        max_requests: Limit the throttle is lowered to (``2`` by default).
            The window is always widened to one hour, see above.
        line: Which line to take the throttle from -- ``'before_auth'``
            (checked before auth, e.g. by IP), ``'after_auth'`` (per-user,
            needs an authenticated request), or ``'any'`` (default, the first
            one checked).

    .. versionadded:: 0.12.0
    """
    endpoint = controller_cls.api_endpoints.get(method)
    if endpoint is None:
        raise ValueError(
            f'{controller_cls.__qualname__} has no endpoint '
            f'for method {method!r}',
        )
    metadata = endpoint.metadata
    match line:
        case 'before_auth':
            throttles = metadata.throttling_before_auth
        case 'after_auth':
            throttles = metadata.throttling_after_auth
        case _:
            throttles = metadata.throttling
    if not throttles:
        raise ValueError(
            f'Endpoint {metadata.operation_id} has no throttling '
            f'to test for line {line!r}',
        )

    original = throttles[0]
    reduced = original.replace(
        max_requests=max_requests,
        duration_in_seconds=Rate.hour,
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
    headers: Mapping[str, HeaderValue] | None = None,
    detail: bool = True,
) -> None:
    """
    Assert that a response was rejected by throttling.

    Collapses the repeated ``429`` status, header and error-body checks into
    a single call::

        assert_throttled(response)  # just the status + `ratelimit` error
        assert_throttled(response, headers={'X-RateLimit-Limit': 2})

    Parameters:
        response: The response to check.
        throttle: Throttle that rejected the request. When given, every header
            its providers report must be present in the response.
        headers: Expected values for response headers, by name.
        detail: Also assert the body is a ``ratelimit`` error. ``True``
            by default; set to ``False`` for custom error models.

    Header names are never hardcoded: which ones are reported depends on the
    throttle's :class:`~dmr.throttling.headers.BaseResponseHeadersProvider`
    instances, so pass the ``throttle`` and they are all checked -- be it
    :class:`~dmr.throttling.headers.XRateLimit`,
    :class:`~dmr.throttling.headers.RateLimitIETFDraft`, or your own provider.
    :func:`assert_throttling` does that for you.

    Values in ``headers`` accept an ``int`` (matched as its string form), a
    ``str``, or any matcher object (e.g. ``dirty_equals.IsStr()``) for
    real-time tests where the exact value is unknown.

    .. versionadded:: 0.12.0
    """
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    if throttle is not None:
        _assert_reported_headers(response.headers, throttle)
    for header_name, expected in (headers or {}).items():
        _assert_header(response.headers, header_name, expected)
    if detail:
        _assert_ratelimit_detail(response)


def assert_throttling(
    controller_cls: 'type[Controller[BaseSerializer]]',
    request_factory: DMRRequestFactory,
    path: str,
    *,
    method: HTTPMethod = HTTPMethod.GET,
    max_requests: int = 2,
    line: ThrottlingLine = 'any',
    headers: Mapping[str, HeaderValue] | None = None,
    detail: bool = True,
) -> HttpResponse:
    """
    Reduce the first throttle, drive requests, and assert the ``429``.

    Sends ``max_requests`` allowed requests, then one that is rejected, and
    checks it with :func:`assert_throttled` -- including every header the
    reduced throttle reports. Returns the ``429`` response, so you can make
    further assertions on it.

    Parameters ``line``, ``headers`` and ``detail`` are passed down
    to :func:`reduced_throttling` and :func:`assert_throttled`.

    .. versionadded:: 0.12.0
    """
    view = controller_cls.as_view()
    build = getattr(request_factory, method.lower())
    with reduced_throttling(
        controller_cls,
        method=method,
        max_requests=max_requests,
        line=line,
    ) as throttle:
        for _ in range(max_requests):
            _assert_ok(view(build(path)))
        throttled = _as_response(view(build(path)))
        assert_throttled(
            throttled,
            throttle=throttle,
            headers=headers,
            detail=detail,
        )
    return throttled


async def assert_async_throttling(
    controller_cls: 'type[Controller[BaseSerializer]]',
    request_factory: DMRAsyncRequestFactory,
    path: str,
    *,
    method: HTTPMethod = HTTPMethod.GET,
    max_requests: int = 2,
    line: ThrottlingLine = 'any',
    headers: Mapping[str, HeaderValue] | None = None,
    detail: bool = True,
) -> HttpResponse:
    """
    Async version of :func:`assert_throttling`.

    .. versionadded:: 0.12.0
    """
    view = controller_cls.as_view()
    build = getattr(request_factory, method.lower())
    with reduced_throttling(
        controller_cls,
        method=method,
        max_requests=max_requests,
        line=line,
    ) as throttle:
        for _ in range(max_requests):
            _assert_ok(await request_factory.wrap(view(build(path))))  # noqa: WPS476
        throttled = _as_response(await request_factory.wrap(view(build(path))))
        assert_throttled(
            throttled,
            throttle=throttle,
            headers=headers,
            detail=detail,
        )
    return throttled


def _swap(
    throttles: tuple[SyncThrottle | AsyncThrottle, ...] | None,
    old: SyncThrottle | AsyncThrottle,
    new: SyncThrottle | AsyncThrottle,
) -> tuple[SyncThrottle | AsyncThrottle, ...] | None:
    if not throttles:
        return throttles
    return tuple(new if throttle is old else throttle for throttle in throttles)


def _assert_reported_headers(
    headers: Any,
    throttle: SyncThrottle | AsyncThrottle,
) -> None:
    for provider in throttle.response_headers:
        for name in provider.provide_headers_specs():
            assert name in headers, (
                f'Header {name!r} reported by '
                f'{type(provider).__qualname__} is missing, '
                f'present headers: {dict(headers)!r}'
            )


def _assert_header(
    headers: Any,
    name: str,
    expected: HeaderValue,
) -> None:
    if isinstance(expected, int):
        expected = str(expected)
    present = dict(headers)
    assert name in headers, (
        f'Header {name!r} is missing, present headers: {present!r}'
    )
    actual = headers[name]
    assert actual == expected, (
        f'Header {name!r}: expected {expected!r}, got {actual!r}'
    )


def _assert_ratelimit_detail(response: HttpResponse) -> None:
    body = json_loads(response.content.decode(response.charset or 'utf8'))
    problems = body['detail']
    assert problems, (
        f'Expected a non-empty `detail` in throttled response, got {body!r}'
    )
    assert all(problem.get('type') == 'ratelimit' for problem in problems), body


def _as_response(candidate: HttpResponseBase) -> HttpResponse:
    assert isinstance(candidate, HttpResponse), candidate
    return candidate


def _assert_ok(candidate: HttpResponseBase) -> None:
    response = _as_response(candidate)
    assert response.status_code == HTTPStatus.OK, response.content
