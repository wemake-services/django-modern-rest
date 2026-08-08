import json
from collections.abc import Callable

import yaml
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import (
    OpenAPIContext,
    build_schema,
    default_config,
    load_schema,
    objects,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


def _external_func(request: HttpRequest) -> HttpResponse:
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

    context = OpenAPIContext(config=default_config())

    external_components = load_schema(
        external_openapi['components'],
        objects.Components,
    )
    context.register_external_components(external_components)

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
        [path('/async', _AsyncController.as_view())],
        external_urls=[
            (
                path(
                    '/allauth/<str:client>/config',
                    _external_func,
                ),
                external_openapi_func,
            ),
            (
                path(
                    '/allauth/<str:client>/auth/login',
                    _ExternalClass.as_view(),
                ),
                external_openapi_class,
            ),
        ],
        tags=['custom'],
    )

    assert len(router.urls) == 3
    assert (
        json.dumps(
            build_schema(
                router,
                context=context,
            ).convert(),
            indent=2,
        )
        == snapshot
    )
