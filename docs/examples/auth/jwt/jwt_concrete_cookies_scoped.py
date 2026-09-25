from django.urls import reverse_lazy

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views

#: The refresh cookie is only sent to the refresh endpoint,
#: `reverse_lazy` keeps this in sync with the urls below:
REFRESH_COOKIE_PATH = reverse_lazy('api:jwt_refresh')

router = Router(
    'api/',
    [
        path(
            'auth/',
            concrete_views.CookieObtainTokensSyncController.as_view(
                serializer=PydanticFastSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_obtain',
        ),
        path(
            'auth/refresh/',
            concrete_views.CookieRefreshTokensSyncController.as_view(
                serializer=PydanticFastSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_refresh',
        ),
        path(
            'auth/logout/',
            concrete_views.CookieLogoutSyncController.as_view(
                serializer=PydanticFastSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_logout',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true, "curl_args": ["-D", "-"], "use_urlpatterns": true}  # noqa: ERA001, E501
