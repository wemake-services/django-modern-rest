import json
from http import HTTPStatus

from django.http import HttpResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security.jwt import HeaderJWTSyncAuth


class _UserController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(return_type=str, status_code=HTTPStatus.OK),
        security=[{'proxyAuth': []}],
    )
    def get(self) -> HttpResponse:
        raise NotImplementedError

    @modify(
        security=[{'gateway': []}],
        auth=(HeaderJWTSyncAuth(),),
    )
    def post(self) -> str:
        raise NotImplementedError


def test_user_provided_security_is_merged(snapshot: SnapshotAssertion) -> None:
    """User-provided security is stored and merged with auth providers."""
    get_meta = _UserController.api_endpoints['GET'].metadata
    post_meta = _UserController.api_endpoints['POST'].metadata
    assert get_meta.security == [{'proxyAuth': []}]
    assert post_meta.security == [{'gateway': []}]

    schema = json.dumps(
        build_schema(
            Router(
                'api/v1/',
                [path('user/', _UserController.as_view())],
            ),
        ).convert(),
        indent=2,
    )
    assert schema == snapshot
