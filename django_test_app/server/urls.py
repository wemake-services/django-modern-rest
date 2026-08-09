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
from server.apps.token_auth import urls as token_auth_urls
from server.apps.token_custom_user import urls as token_custom_user_urls

router = Router(prefix='api/')
router.include(model_simple_urls.router, namespace='model_simple')
router.include(model_fk_urls.router, namespace='model_fk')
router.include(middleware_urls.router, namespace='middlewares')
router.include(controllers_urls.router, namespace='controllers')
router.include(negotiations_urls.router, namespace='negotiations')
router.include(jwt_auth_urls.router, namespace='jwt_auth')
router.include(django_session_auth_urls.router, namespace='django_session_auth')
router.include(token_auth_urls.router, namespace='token_auth')
router.include(token_custom_user_urls.router, namespace='token_custom_user')
router.include(etag_urls.router, namespace='etag')

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
