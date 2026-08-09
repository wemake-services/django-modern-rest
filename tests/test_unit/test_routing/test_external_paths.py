import json
from collections.abc import Callable

import pydantic
import pytest
import yaml
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller
from dmr.openapi import OpenAPIConfig, build_schema, load_schema, objects
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, external_path


def _external_func(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


def _hidden_func(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


class _ExternalClass(View):
    def post(self, request: HttpRequest, user_id: int) -> HttpResponse:
        raise NotImplementedError


class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> list[int]:
        raise NotImplementedError


def test_external_paths_schema(  # noqa: WPS210
    snapshot: SnapshotAssertion,
    named_text_fixture: Callable[[str], str],
) -> None:
    """Ensure that schema is correct for external paths."""
    external_openapi = yaml.safe_load(
        named_text_fixture('django-allauth.yml'),
    )

    config = OpenAPIConfig(
        title='Your Awesome Project',
        version='0.1.0',
        components=load_schema(
            external_openapi['components'],
            objects.Components,
        ),
    )

    external_openapi_func = load_schema(
        external_openapi['paths']['/_allauth/{client}/v1/config'],
        objects.PathItem,
    )

    external_openapi_class = load_schema(
        external_openapi['paths']['/_allauth/{client}/v1/auth/login'],
        objects.PathItem,
    )

    router = Router(
        'api/v1/',
        urls=[
            # Order is important:
            external_path(
                '/allauth/<str:client>/config',
                _external_func,
                openapi=external_openapi_func,
            ),
            path('/async', _AsyncController.as_view()),
            external_path(
                '/allauth/<str:client>/auth/login',
                _ExternalClass.as_view(),
                openapi=external_openapi_class,
            ),
            # Won't be present in the final OpenAPI, because it is hidden:
            external_path('/hidden', _hidden_func, openapi=None),
        ],
        tags=['custom'],
    )

    assert len(router.urls) == 4
    assert (
        json.dumps(
            build_schema(
                router,
                config=config,
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _User(pydantic.BaseModel):
    email: str


class _UserController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[_User]) -> _User:
        raise NotImplementedError


def test_external_paths_schema_duplicate() -> None:
    """Ensure that schema is can't produce duplicates silently."""
    router = Router(
        'api/v1/',
        [path('/user', _UserController.as_view())],
    )

    config = OpenAPIConfig(
        title='Your Awesome Project',
        version='0.1.0',
        components=objects.Components(schemas={'_User': objects.Schema()}),
    )

    with pytest.raises(ValueError, match='_User'):
        build_schema(router, config=config)
