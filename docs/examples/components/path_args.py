from typing import TypeAlias

import pydantic
from django.urls import include, re_path

from dmr import Controller, Path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path

_IntArgs: TypeAlias = tuple[int, ...]
_PathModel: TypeAlias = pydantic.RootModel[_IntArgs]


class ItemController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_PathModel]) -> list[int]:
        return list(parsed_path.root)


class _DayPath(pydantic.BaseModel):
    day: int


class DayItemController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_DayPath]) -> _DayPath:
        return parsed_path


router = Router(
    'api/',
    [
        re_path(
            r'^items/(\d+)/(\d+)/$',
            ItemController.as_view(),
            name='items',
        ),
        re_path(
            r'^items/(\d+)/(\d+)/(?P<day>[0-9]{2})/$',
            DayItemController.as_view(),
            name='day-items',
        ),
    ],
)
schema = build_schema(router)

urlpatterns = [
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "ItemController", "method": "get", "url": "/api/items/10/20/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "DayItemController", "method": "get", "url": "/api/items/10/20/25/", "use_urlpatterns": true}  # noqa: ERA001, E501
# No ``# openapi:`` preview: ``build_schema`` cannot yet resolve unnamed
# ``re_path`` groups (see ``test_args_path_schema`` xfail in the test suite).
