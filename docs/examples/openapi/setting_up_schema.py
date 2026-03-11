from django.urls import include, path

from dmr.openapi import build_schema
from dmr.openapi.views import (
    OpenAPIJsonView,
    RedocView,
    ScalarView,
    SwaggerView,
)
from dmr.routing import Router
from examples.getting_started.msgspec_controller import UserController

router = Router(
    [
        path('user/', UserController.as_view(), name='users'),
    ],
    prefix='api/',
)
schema = build_schema(router)

urlpatterns = [
    path(router.prefix, include((router.urls, 'your_app'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
    path('docs/scalar/', ScalarView.as_view(schema), name='scalar'),
    path('docs/redoc/', RedocView.as_view(schema), name='redoc'),
]
