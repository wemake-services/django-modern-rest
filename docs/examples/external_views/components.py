import random

from django.http import HttpRequest, JsonResponse
from django.urls import include
from django.views.decorators.http import require_GET

from dmr.openapi import OpenAPIConfig, build_schema, load_schema
from dmr.openapi.objects import Components, PathItem, Tag
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, external_path, path
from examples.external_views.read_openapi import read_openapi_yaml


@require_GET
def number(request: HttpRequest, start: int, end: int) -> JsonResponse:
    return JsonResponse(random.randint(start, end), safe=False)


# Now, load the schema:
raw_schema = read_openapi_yaml('openapi2.yml')

# Create a router and URL patterns:
router = Router(
    'api/',
    urls=[
        external_path(
            'number/<int:start>/<int:end>/',
            number,
            name='number',
            openapi=load_schema(
                raw_schema['paths']['/api/random/{start}/{end}'],
                PathItem,
            ),
        ),
    ],
)

# Register external components to the config:

config = OpenAPIConfig(
    title='New Random Number API',
    version='0.0.1',
    # Here you can pass any `OpenAPI` class parameters,
    # not just components and tags:
    components=load_schema(raw_schema['components'], Components),
    tags=[load_schema(tag, Tag) for tag in raw_schema['tags']],
)
schema = build_schema(router, config=config)

urlpatterns = [
    # Register our router in the final url patterns:
    path(router.prefix, include((router.urls, 'test_app'), namespace='api')),
    # Add swagger:
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# run: {"controller": "number", "method": "get", "url": "/api/number/1/5/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "number", "method": "get", "url": "/api/number/regular-django/url-error/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "assert-error-text": "404", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
