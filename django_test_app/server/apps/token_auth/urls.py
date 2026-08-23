from dmr.routing import Router, path
from server.apps.token_auth.views import example, obtain

router = Router(
    'token-auth/',
    [
        path(
            'token-sync-auth/',
            example.ControllerWithTokenSyncAuth.as_view(),
            name='token_sync_auth',
        ),
        path(
            'token-obtain-sync/',
            obtain.CustomObtainTokenSyncController.as_view(),
            name='token_obtain_sync',
        ),
        path(
            'token-obtain-async/',
            obtain.CustomObtainTokenAsyncController.as_view(),
            name='token_obtain_async',
        ),
        path(
            'token-custom-sync-auth/',
            obtain.ControllerCustomTokenSync.as_view(),
            name='token_custom_sync_auth',
        ),
    ],
    tags=['token_auth'],
)
