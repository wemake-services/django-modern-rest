from typing import Final

from django.views.decorators.cache import cache_page

from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.openapi.views.yaml import OpenAPIYamlView
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

_CACHE_TIMEOUT: Final = 900  # 15 minutes


router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)
schema = build_schema(router)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path(
        'docs/openapi.json/',
        cache_page(_CACHE_TIMEOUT)(OpenAPIJsonView.as_view(schema)),
        name='openapi_json',
    ),
    path(
        'docs/openapi.yaml/',
        cache_page(_CACHE_TIMEOUT)(OpenAPIYamlView.as_view(schema)),
        name='openapi_yaml',
    ),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
