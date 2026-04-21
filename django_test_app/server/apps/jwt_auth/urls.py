from dmr.routing import Router, path
from server.apps.jwt_auth import views

router = Router(
    'jwt-auth/',
    [
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
            'jwt-refresh-sync/',
            views.RefreshSyncController.as_view(),
            name='jwt_refresh_sync',
        ),
        path(
            'jwt-refresh-async/',
            views.RefreshAsyncController.as_view(),
            name='jwt_refresh_async',
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
    ],
)
