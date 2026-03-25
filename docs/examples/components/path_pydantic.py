from typing import Annotated

import pydantic
from django.urls import include
from typing_extensions import TypedDict

from dmr import Controller, Path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class _PathModel(TypedDict):
    user_id: Annotated[str, pydantic.Field(min_length=4, max_length=4)]
    post_id: Annotated[int, pydantic.Field(gt=0)]


class PostController(
    Controller[PydanticSerializer],
):
    def get(self, parsed_path: Path[_PathModel]) -> _PathModel:
        return parsed_path


router = Router(
    'api/',
    [
        # We define a regular Django path:
        path(
            'user/<str:user_id>/post/<int:post_id>/',
            PostController.as_view(),
            name='user',
        ),
    ],
)
schema = build_schema(router)

urlpatterns = [
    # Register our router in the final url patterns:
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    # Add swagger:
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "PostController", "method": "get", "url": "/api/user/abcd/post/1/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "PostController", "method": "get", "url": "/api/user/abcd/post/0/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001, E501
