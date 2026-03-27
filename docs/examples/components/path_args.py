import pydantic
from django.urls import include, re_path

from dmr import Controller, Path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path

_IntArgs = tuple[int, ...]
_ArgsRoot = tuple[_IntArgs, dict[str, str]]


class _ArgsPath(pydantic.RootModel[_ArgsRoot]):
    """Accepts unnamed regex groups as a tuple of ints plus empty kwargs."""


class ItemController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_ArgsPath]) -> list[int]:
        args, _kwargs = parsed_path.root
        return list(args)


router = Router(
    'api/',
    [
        re_path(
            r'^items/(\d+)/(\d+)/$',
            ItemController.as_view(),
            name='items',
        ),
    ],
)
schema = build_schema(router)

urlpatterns = [
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "ItemController", "method": "get", "url": "/api/items/10/20/", "use_urlpatterns": true}  # noqa: ERA001, E501
