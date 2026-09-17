from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views

#: The refresh cookie is only sent to the refresh endpoint,
#: `reverse_lazy` keeps this in sync with the urls below:
REFRESH_COOKIE_PATH = reverse_lazy('api:jwt_refresh')


class ObtainCookiesController(
    concrete_views.CookieObtainTokensSyncController[PydanticSerializer],
):
    """Authenticates a user and sets both token cookies."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH


class RefreshCookiesController(
    concrete_views.CookieRefreshTokensSyncController[PydanticSerializer],
):
    """Reads the refresh cookie and rotates both cookies."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH


class LogoutCookiesController(
    concrete_views.CookieLogoutSyncController[PydanticSerializer],
):
    """Sends both cookies back empty and already expired."""

    jwt_refresh_cookie_path = REFRESH_COOKIE_PATH


router = Router(
    'api/',
    [
        path('auth/', ObtainCookiesController.as_view(), name='jwt_obtain'),
        path(
            'auth/refresh/',
            RefreshCookiesController.as_view(),
            name='jwt_refresh',
        ),
        path(
            'auth/logout/',
            LogoutCookiesController.as_view(),
            name='jwt_logout',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"controller": "ObtainCookiesController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "curl_args": ["-D", "-"], "use_urlpatterns": true}  # noqa: ERA001, E501
