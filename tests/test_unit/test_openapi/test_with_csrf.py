import json
from http import HTTPStatus

from django.conf import LazySettings
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings


def test_csrf_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for controller with csrf."""

    class _UserController(Controller[PydanticSerializer]):
        csrf_exempt = False

        def post(self) -> str:
            raise NotImplementedError

        def get(self) -> int:
            raise NotImplementedError

    metadata = _UserController.api_endpoints['GET'].metadata

    assert HTTPStatus.FORBIDDEN not in metadata.responses
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('user/', _UserController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


def test_disabled_csrf_schema(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema is correct for controller with ignored 403."""
    settings.DMR_SETTINGS = {
        Settings.exclude_semantic_responses: {HTTPStatus.FORBIDDEN},
    }

    class _CustomController(Controller[PydanticSerializer]):
        csrf_exempt = False

        def post(self) -> str:
            raise NotImplementedError

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('user/', _CustomController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


def test_disabled_csrf_no_provider(
    snapshot: SnapshotAssertion,
    settings: LazySettings,
) -> None:
    """Ensure that schema is correct for csrf and no provider."""
    settings.DMR_SETTINGS = {
        Settings.semantic_schema_providers: [],
    }

    class _CustomController(Controller[PydanticSerializer]):
        csrf_exempt = False

        def post(self) -> str:
            raise NotImplementedError

    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('custom/', _CustomController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
