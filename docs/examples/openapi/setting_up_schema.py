from django.urls import include

from dmr.openapi import build_schema
from dmr.openapi.views import (
    OpenAPIJsonView,
    RedocView,
    ScalarView,
    StoplightView,
    SwaggerView,
)
from dmr.openapi.views.yaml import OpenAPIYamlView
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

# Build the schema once and reuse it across all docs views.
schema = build_schema(router)

urlpatterns = [
    # Mount the actual API endpoints.
    path(router.prefix, include((router.urls, 'your_app'), namespace='api')),
    # Machine-readable schema outputs for tooling and client generation.
    path(
        'docs/openapi.json/',
        OpenAPIJsonView.as_view(schema),
        name='openapi_json',
    ),
    path(  # Requires the `django-modern-rest[openapi]` extra.
        'docs/openapi.yaml/',
        OpenAPIYamlView.as_view(schema),
        name='openapi_yaml',
    ),
    # Human-friendly documentation UIs backed by the same schema.
    path('docs/stoplight/', StoplightView.as_view(schema), name='stoplight'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
    path('docs/scalar/', ScalarView.as_view(schema), name='scalar'),
    path('docs/redoc/', RedocView.as_view(schema), name='redoc'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
