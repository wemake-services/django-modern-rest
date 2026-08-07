import json
from pathlib import Path
from typing import Any, Final

import yaml
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import OpenAPIContext, build_schema, default_config, objects
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


def load_openapi_schema(
    unstructured: Any,
    model: type[Any],
    serializer: type[PydanticSerializer],
) -> Any:
    return serializer.from_python(
        unstructured,
        model,
        strict=False,
        extra_namespace=objects.__dict__,
    )


_EXTERNAL_OPENAPI: Final = yaml.safe_load(
    Path(__file__).parent.joinpath('django_allauth.yml').read_bytes(),
)

_CONTEXT: Final = OpenAPIContext(config=default_config())

_CONTEXT.register_external_schemas(
    load_openapi_schema(
        _EXTERNAL_OPENAPI['components'],
        objects.Components,
        serializer=PydanticSerializer,
    ),
)

Path('components.txt').write_text(str(_CONTEXT.get_components()))

_EXTERNAL_FUNC_OPENAPI: Final = load_openapi_schema(
    _EXTERNAL_OPENAPI['paths']['/_allauth/{client}/v1/config'],
    objects.PathItem,
    serializer=PydanticSerializer,
)


def _external_func(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


_EXTERNAL_CLASS_OPENAPI: Final = load_openapi_schema(
    _EXTERNAL_OPENAPI['paths']['/_allauth/{client}/v1/auth/login'],
    objects.PathItem,
    serializer=PydanticSerializer,
)

Path('filepath.txt').write_text(str(_EXTERNAL_CLASS_OPENAPI))


class _ExternalClass(View):
    def post(self, request: HttpRequest, user_id: int) -> HttpResponse:
        raise NotImplementedError


class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> list[int]:
        raise NotImplementedError


def test_external_paths_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for external paths."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/async', _AsyncController.as_view())],
                    external_urls=[
                        (
                            path(
                                '/_allauth/<str:client>/v1/config',
                                _external_func,
                            ),
                            _EXTERNAL_FUNC_OPENAPI,
                        ),
                        (
                            path(
                                '/_allauth/<str:client>/v1/auth/login',
                                _ExternalClass.as_view(),
                            ),
                            _EXTERNAL_CLASS_OPENAPI,
                        ),
                    ],
                    tags=['custom'],
                ),
                context=_CONTEXT,
            ).convert(skip_validation=True),
            indent=2,
        )
        == snapshot
    )
