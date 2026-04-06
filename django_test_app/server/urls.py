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
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, build_404_handler, build_500_handler, path
from server.apps.controllers import urls as controllers_urls
from server.apps.django_session_auth import urls as django_session_auth_urls
from server.apps.etag import urls as etag_urls
from server.apps.jwt_auth import urls as jwt_auth_urls
from server.apps.middlewares import urls as middleware_urls
from server.apps.model_fk import urls as model_fk_urls
from server.apps.model_simple import urls as model_simple_urls
from server.apps.negotiations import urls as negotiations_urls
from server.apps.openapi.config import get_config

router = Router(
    prefix='api/',
    urls=[
        path(
            model_simple_urls.router.prefix,
            include(
                (model_simple_urls.router.urls, 'model_simple'),
                namespace='model_simple',
            ),
        ),
        path(
            model_fk_urls.router.prefix,
            include(
                (model_fk_urls.router.urls, 'model_fk'),
                namespace='model_fk',
            ),
        ),
        path(
            middleware_urls.router.prefix,
            include(
                (middleware_urls.router.urls, 'middlewares'),
                namespace='middlewares',
            ),
        ),
        path(
            controllers_urls.router.prefix,
            include(
                (controllers_urls.router.urls, 'controllers'),
                namespace='controllers',
            ),
        ),
        path(
            negotiations_urls.router.prefix,
            include(
                (negotiations_urls.router.urls, 'negotiations'),
                namespace='negotiations',
            ),
        ),
        path(
            jwt_auth_urls.router.prefix,
            include(
                (jwt_auth_urls.router.urls, 'jwt_auth'),
                namespace='jwt_auth',
            ),
        ),
        path(
            django_session_auth_urls.router.prefix,
            include(
                (django_session_auth_urls.router.urls, 'django_session_auth'),
                namespace='django_session_auth',
            ),
        ),
        path(
            etag_urls.router.prefix,
            include(
                (etag_urls.router.urls, 'etag'),
                namespace='etag',
            ),
        ),
    ],
)

schema = build_schema(router, config=get_config())

urlpatterns = [
    path(router.prefix, include((router.urls, 'server'), namespace='api')),
    path(
        'docs/openapi.json/',
        OpenAPIJsonView.as_view(schema),
        name='openapi_json',
    ),
    path(
        'docs/openapi.yaml/',
        OpenAPIYamlView.as_view(schema),
        name='openapi_yaml',
    ),
    path('docs/redoc/', RedocView.as_view(schema), name='redoc'),
    path('docs/scalar/', ScalarView.as_view(schema), name='scalar'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
    path('docs/stoplight/', StoplightView.as_view(schema), name='stoplight'),
]

handler404 = build_404_handler(
    router.prefix,
    serializer=PydanticSerializer,
)

handler500 = build_500_handler(
    router.prefix,
    serializer=PydanticSerializer,
)
