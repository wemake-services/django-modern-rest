from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views

router = Router(
    'api/',
    [
        # Every one of them also has an `Async` version:
        path(
            'auth/',
            concrete_views.CookieObtainTokensSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_obtain',
        ),
        path(
            'auth/refresh/',
            concrete_views.CookieRefreshTokensSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_refresh',
        ),
        path(
            'auth/logout/',
            concrete_views.CookieLogoutSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_logout',
        ),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path(
        'docs/openapi.json/',
        OpenAPIJsonView.as_view(build_schema(router)),
        name='openapi_json',
    ),
]

# run: {"method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "curl_args": ["-D", "-"], "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
