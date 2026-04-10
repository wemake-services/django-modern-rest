import json

from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.throttling import Rate, SyncThrottle


class _SyncEndpointController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle((1, Rate.second)),
    ]

    def get(self) -> str:
        raise NotImplementedError


def test_throttled_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for throttled controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('/user', _SyncEndpointController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
