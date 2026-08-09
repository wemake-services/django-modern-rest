import random

from django.http import HttpRequest, JsonResponse
from django.urls import include
from django.views.decorators.http import require_GET

from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, external_path, path


@require_GET
def number(request: HttpRequest) -> JsonResponse:
    return JsonResponse(random.randint(1, 10), safe=False)


# Create a router and URL patterns:
router = Router(
    'api/',
    urls=[
        # This function will still work, but be ignored from the spec:
        external_path('number/', number, name='number', openapi=None),
    ],
)
schema = build_schema(router)

urlpatterns = [
    # Register our router in the final url patterns:
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    # Add swagger:
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "number", "method": "get", "url": "/api/number/", "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
