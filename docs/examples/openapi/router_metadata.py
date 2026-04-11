from django.urls import include

from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

router = Router(
    'api/v1/users/',
    [
        path('', UserController.as_view()),
        path('<int:user_id>/', UserController.as_view()),
    ],
    tags=['users'],  # All endpoints tagged as 'users'
    deprecated=True,  # All endpoints are deprecated
)
schema = build_schema(router)

urlpatterns = [
    # Register our router in the final url patterns:
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    # Add swagger:
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
