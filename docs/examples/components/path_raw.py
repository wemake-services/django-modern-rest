import uuid
from typing import Any, assert_type

import pydantic
from django.urls import include

from dmr import Controller
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class _PostModel(pydantic.BaseModel):
    user_id: int
    post_id: uuid.UUID


class PostController(Controller[PydanticSerializer]):
    def get(self) -> _PostModel:
        assert_type(self.kwargs, dict[str, Any])
        return _PostModel(
            user_id=self.kwargs['user_id'],
            post_id=self.kwargs['post_id'],
        )


router = Router(
    'api/',
    [
        # We define a regular Django path:
        path(
            'user/<int:user_id>/post/<uuid:post_id>/',
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
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
]

# run: {"controller": "PostController", "method": "get", "url": "/api/user/1/post/8b36dfc2-f168-47db-827a-7ae323539936/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "PostController", "method": "get", "url": "/api/user/1/post/wrong/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001, E501
