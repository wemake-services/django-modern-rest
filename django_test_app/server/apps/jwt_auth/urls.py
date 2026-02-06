from django.urls import path

from django_modern_rest.routing import Router
from server.apps.jwt_auth import views

router = Router([
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
