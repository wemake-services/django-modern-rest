from django.urls import reverse_lazy
from typing_extensions import override

from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.jwt.views import (
    CookieObtainTokensSyncController,
    ObtainTokensPayload,
)
from examples.auth.jwt.jwt_cookie_refresh import RefreshCookiesSyncController


# You can also use `CookieObtainTokensAsyncController` if needed:
class ObtainCookiesSyncController(
    CookieObtainTokensSyncController[
        PydanticSerializer,
        ObtainTokensPayload,
    ],
):
    # The refresh cookie is only sent to the refresh endpoint,
    # `reverse_lazy` keeps this in sync with the urls below:
    jwt_refresh_cookie_path = reverse_lazy('api:jwt_refresh')

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload


router = Router(
    'api/',
    [
        path('auth/', ObtainCookiesSyncController.as_view(), name='jwt_obtain'),
        path(
            'auth/refresh/',
            RefreshCookiesSyncController.as_view(),
            name='jwt_refresh',
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

# run: {"controller": "ObtainCookiesSyncController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "curl_args": ["-D", "-"], "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
