from http import HTTPMethod
from unittest import mock

import pytest

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


class _NoChecksSyncController(Controller[PydanticFastSerializer]):
    def get(self) -> str:
        return 'ok'


class _NoChecksAsyncController(Controller[PydanticFastSerializer]):
    async def get(self) -> str:
        return 'ok'


class _WithChecksSyncController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[SyncThrottle(100, Rate.second)],
        auth=[DjangoSessionSyncAuth()],
    )
    def get(self) -> str:
        return 'ok'


class _WithChecksAsyncController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[AsyncThrottle(100, Rate.second)],
        auth=[DjangoSessionAsyncAuth()],
    )
    async def get(self) -> str:
        return 'ok'


def test_sync_checks_skipped_when_not_configured(
    dmr_rf: DMRRequestFactory,
) -> None:
    """`_run_checks` must not call parts that are not configured."""
    endpoint = _NoChecksSyncController.api_endpoints[str(HTTPMethod.GET)]
    with (
        mock.patch.object(type(endpoint), '_run_throttle_before') as before,
        mock.patch.object(type(endpoint), '_run_auth') as auth,
        mock.patch.object(type(endpoint), '_run_throttle_after') as after,
    ):
        response = _NoChecksSyncController.as_view()(
            dmr_rf.get('/whatever/'),
        )
        assert response.status_code == 200  # noqa: WPS432
        before.assert_not_called()
        auth.assert_not_called()
        after.assert_not_called()


async def test_async_checks_skipped_when_not_configured(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """`_run_async_checks` must not await parts that are not configured."""
    endpoint = _NoChecksAsyncController.api_endpoints[str(HTTPMethod.GET)]
    with (
        mock.patch.object(
            type(endpoint),
            '_run_async_throttle_before',
        ) as before,
        mock.patch.object(type(endpoint), '_run_async_auth') as auth,
        mock.patch.object(
            type(endpoint),
            '_run_async_throttle_after',
        ) as after,
    ):
        response = await dmr_async_rf.wrap(
            _NoChecksAsyncController.as_view()(dmr_async_rf.get('/whatever/')),
        )
        assert response.status_code == 200  # noqa: WPS432
        before.assert_not_called()
        auth.assert_not_called()
        after.assert_not_called()


def test_sync_checks_run_when_configured(
    dmr_rf: DMRRequestFactory,
) -> None:
    """`_run_checks` must call every configured part exactly once."""
    endpoint = _WithChecksSyncController.api_endpoints[str(HTTPMethod.GET)]
    with (
        mock.patch.object(
            type(endpoint),
            '_run_throttle_before',
            wraps=endpoint._run_throttle_before,
        ) as before,
        mock.patch.object(
            type(endpoint),
            '_run_auth',
            wraps=endpoint._run_auth,
        ) as auth,
        mock.patch.object(
            type(endpoint),
            '_run_throttle_after',
            wraps=endpoint._run_throttle_after,
        ) as after,
    ):
        # Auth is expected to fail (no session), we only care that every
        # configured check was actually invoked, not about the outcome.
        _WithChecksSyncController.as_view()(dmr_rf.get('/whatever/'))
        before.assert_called_once()
        auth.assert_called_once()
        after.assert_not_called()  # auth raised: throttle-after never runs


@pytest.mark.django_db
async def test_async_checks_run_when_configured(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """`_run_async_checks` must await every configured part exactly once."""
    endpoint = _WithChecksAsyncController.api_endpoints[str(HTTPMethod.GET)]
    with (
        mock.patch.object(
            type(endpoint),
            '_run_async_throttle_before',
            wraps=endpoint._run_async_throttle_before,
        ) as before,
        mock.patch.object(
            type(endpoint),
            '_run_async_auth',
            wraps=endpoint._run_async_auth,
        ) as auth,
        mock.patch.object(
            type(endpoint),
            '_run_async_throttle_after',
            wraps=endpoint._run_async_throttle_after,
        ) as after,
    ):
        await dmr_async_rf.wrap(
            _WithChecksAsyncController.as_view()(
                dmr_async_rf.get('/whatever/'),
            ),
        )
        before.assert_called_once()
        auth.assert_called_once()
        after.assert_not_called()
