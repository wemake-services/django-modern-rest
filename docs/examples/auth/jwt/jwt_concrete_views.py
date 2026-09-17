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
            concrete_views.ObtainTokensSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_obtain',
        ),
        path(
            'auth/refresh/',
            concrete_views.RefreshTokenSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_refresh',
        ),
        path(
            'auth/verify/',
            concrete_views.VerifyTokenSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='jwt_verify',
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

# run: {"method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
