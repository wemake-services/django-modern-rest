from django.urls import include

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import Server
from dmr.openapi.views import (
    OpenAPIJsonView,
    RedocView,
    ScalarView,
    StoplightView,
    SwaggerView,
)
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

config = OpenAPIConfig(
    title='My awesome API',
    version='1.0.0',
    openapi_version='3.2.0',
    servers=[
        Server(url='https://prod.example.com'),
        Server(url='https://dev.example.com'),
    ],
)
schema = build_schema(router, config=config)

urlpatterns = [
    path(router.prefix, include((router.urls, 'your_app'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
    path('docs/scalar/', ScalarView.as_view(schema), name='scalar'),
    path('docs/redoc/', RedocView.as_view(schema), name='redoc'),
    path('docs/stoplight/', StoplightView.as_view(schema), name='stoplight'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
