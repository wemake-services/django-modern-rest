import json

from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, modify
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


class _SyncController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second),
    ]

    def get(self) -> str:
        raise NotImplementedError


class _XAsyncThrottle(AsyncThrottle):
    header_prefix = 'X-'


class _AsyncController(Controller[PydanticSerializer]):
    @modify(
        throttling=[
            _XAsyncThrottle(1, Rate.second),
            _XAsyncThrottle(5, Rate.minute),
        ],
    )
    async def get(self) -> str:
        raise NotImplementedError


def test_throttled_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for throttled controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('/sync', _SyncController.as_view()),
                        path('/async', _AsyncController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
