from collections.abc import Callable
from contextlib import AbstractContextManager
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, Protocol, TypeAlias

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer
    from dmr.throttling import AsyncThrottle, Rate, SyncThrottle

ThrottlingWhen: TypeAlias = Literal['any', 'before_auth', 'after_auth']


class AssertThrottlingFixture(Protocol):
    """Type of the ``dmr_assert_throttling`` fixture."""

    def __call__(  # noqa: D102
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        request_factory: Callable[[], HttpRequest],
        *,
        max_requests: int = 2,
        rate: 'Rate' = ...,
        when: ThrottlingWhen = 'any',
        success_status: HTTPStatus | None = None,
    ) -> tuple[HttpResponse, 'SyncThrottle']: ...


class AssertAsyncThrottlingFixture(Protocol):
    """Type of the ``dmr_assert_async_throttling`` fixture."""

    async def __call__(  # noqa: D102
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        request_factory: Callable[[], HttpRequest],
        *,
        max_requests: int = 2,
        rate: 'Rate' = ...,
        when: ThrottlingWhen = 'any',
        success_status: HTTPStatus | None = None,
    ) -> tuple[HttpResponse, 'AsyncThrottle']: ...


class ReducedThrottlingFixture(Protocol):
    """Type of the ``dmr_reduced_throttling`` fixture."""

    def __call__(  # noqa: D102
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        *,
        method: str,
        max_requests: int = 2,
        rate: 'Rate' = ...,
        when: ThrottlingWhen = ...,
    ) -> AbstractContextManager['SyncThrottle | AsyncThrottle']: ...
