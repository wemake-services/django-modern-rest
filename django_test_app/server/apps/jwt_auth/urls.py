from django.urls import path

from dmr.routing import Router
from server.apps.jwt_auth import views

router = Router([
    path(
        'jwt-obtain-access-refresh-sync/',
        views.ObtainAccessAndRefreshSyncController.as_view(),
        name='jwt_obtain_access_refresh_sync',
    ),
    path(
        'jwt-obtain-access-refresh-async/',
        views.ObtainAccessAndRefreshAsyncController.as_view(),
        name='jwt_obtain_access_refresh_async',
    ),
    path(
        'jwt-sync-auth/',
        views.ControllerWithJWTSyncAuth.as_view(),
        name='jwt_sync_auth',
    ),
    path(
        'jwt-async-auth/',
        views.ControllerWithJWTAsyncAuth.as_view(),
        name='jwt_async_auth',
    ),
])
