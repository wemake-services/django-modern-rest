import uuid
from http import HTTPStatus
from typing import Any, assert_type

import pydantic
from django.urls import include

from dmr import APIError, Controller
from dmr.errors import ErrorType
from dmr.metadata import ResponseSpec
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class _PostModel(pydantic.BaseModel):
    user_id: int
    post_id: uuid.UUID


class PostController(Controller[PydanticSerializer]):
    responses = (
        ResponseSpec(
            Controller.error_model,
            status_code=HTTPStatus.NOT_FOUND,
        ),
    )

    def get(self) -> _PostModel:
        assert_type(self.kwargs, dict[str, Any])
        if self.kwargs['user_id'] <= 0:
            # Here we simulate some logical error, when object is not found:
            raise APIError(
                self.format_error(
                    'Page not found',
                    error_type=ErrorType.not_found,
                ),
                status_code=HTTPStatus.NOT_FOUND,
            )
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
]

# run: {"controller": "PostController", "method": "get", "url": "/api/user/1/post/8b36dfc2-f168-47db-827a-7ae323539936/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "PostController", "method": "get", "url": "/api/user/1/post/wrong/", "use_urlpatterns": true, "assert-error-text": "Page not found", "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "PostController", "method": "get", "url": "/api/user/0/post/8b36dfc2-f168-47db-827a-7ae323539936/", "use_urlpatterns": true, "assert-error-text": "Page not found", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001, E501
