from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views


# Every one of them also has an `Async` version:
class ObtainTokensController(
    concrete_views.ObtainTokensSyncController[PydanticSerializer],
):
    """Authenticates a user and issues both tokens."""


class RefreshTokensController(
    concrete_views.RefreshTokenSyncController[PydanticSerializer],
):
    """Issues a new pair of tokens for a valid refresh token."""


class VerifyTokenController(
    concrete_views.VerifyTokenSyncController[PydanticSerializer],
):
    """Answers with ``204`` when the access token is still valid."""


router = Router(
    'api/',
    [
        path('auth/', ObtainTokensController.as_view(), name='jwt_obtain'),
        path(
            'auth/refresh/',
            RefreshTokensController.as_view(),
            name='jwt_refresh',
        ),
        path(
            'auth/verify/',
            VerifyTokenController.as_view(),
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

# run: {"controller": "ObtainTokensController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
