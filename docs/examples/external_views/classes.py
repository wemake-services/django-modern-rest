import random

from django.http import HttpRequest, JsonResponse
from django.views import View

from dmr.openapi import build_schema, load_schema
from dmr.openapi.objects import PathItem
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, external_path, path
from examples.external_views.read_openapi import read_openapi_yaml


class NumberView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(random.randint(1, 10), safe=False)


# Now, load the schema:
raw_schema = read_openapi_yaml('openapi.yml')

# Create a router and URL patterns:
router = Router(
    'api/',
    urls=[
        external_path(
            'number/',
            NumberView.as_view(),
            name='number',
            openapi=load_schema(raw_schema['paths']['/api/number'], PathItem),
        ),
    ],
)
schema = build_schema(router)

urlpatterns = [
    # Register our router in the final url patterns:
    router.to_urlpatterns(namespace='api'),
    # Add swagger:
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "NumberView", "method": "get", "url": "/api/number/", "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
