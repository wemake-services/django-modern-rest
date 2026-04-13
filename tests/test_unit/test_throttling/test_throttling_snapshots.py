import json
from http import HTTPStatus
from typing import Annotated

from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, validate
from dmr.errors import ErrorModel
from dmr.metadata import ResponseSpecMetadata
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft, RetryAfter, XRateLimit


class _DefaultController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second),
    ]

    def get(self) -> str:
        raise NotImplementedError


class _AllHeadersController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(
            1,
            Rate.second,
            response_headers=(XRateLimit(), RateLimitIETFDraft(), RetryAfter()),
        ),
    ]

    def get(self) -> str:
        raise NotImplementedError


class _NoHeadersController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(
            1,
            Rate.second,
            response_headers=(),
        ),
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
                        path('/default', _DefaultController.as_view()),
                        path('/all', _AllHeadersController.as_view()),
                        path('/no', _NoHeadersController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _AllReportsController(Controller[PydanticSerializer]):
    error_model = Annotated[
        ErrorModel,
        ResponseSpecMetadata(
            headers=RateLimitIETFDraft().provide_headers_specs(),
        ),
    ]

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            headers=RateLimitIETFDraft().provide_headers_specs(),
        ),
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                response_headers=[RateLimitIETFDraft()],
                cache_key=RemoteAddr(name='per-second'),
            ),
        ],
    )
    def get(self) -> HttpResponse:
        raise NotImplementedError


def test_throttled_schema_with_errors(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for controller with custom errors."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('/with-errors', _AllReportsController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
