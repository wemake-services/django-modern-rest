import random

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from dmr import Controller
from dmr.openapi import build_schema, load_schema
from dmr.openapi.objects import PathItem
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, external_path, path
from examples.external_views.read_openapi import read_openapi_yaml


class NumberController(Controller[PydanticFastSerializer]):
    def get(self) -> int:
        return random.randint(1, 10)


@require_GET
def number(request: HttpRequest) -> JsonResponse:
    return JsonResponse(random.randint(1, 10), safe=False)


# Now, load the schema:
raw_schema = read_openapi_yaml('openapi.yml')

# Create a router and URL patterns:
router = Router(
    'api/',
    urls=[
        path('dmr-number/', NumberController.as_view(), name='dmr_number'),
        external_path(
            'number/',
            number,
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

# run: {"controller": "NumberController", "method": "get", "url": "/api/dmr-number/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "number", "method": "get", "url": "/api/number/", "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
