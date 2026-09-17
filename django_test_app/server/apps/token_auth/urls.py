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
            'token-default-sync-auth/',
            example.ControllerWithDefaultTokenSyncAuth.as_view(),
            name='token_default_sync_auth',
        ),
        path(
            'token-concrete-obtain-sync/',
            obtain.ConcreteObtainTokenSyncController.as_view(),
            name='token_concrete_obtain_sync',
        ),
        path(
            'token-concrete-obtain-async/',
            obtain.ConcreteObtainTokenAsyncController.as_view(),
            name='token_concrete_obtain_async',
        ),
        path(
            'token-custom-sync-auth/',
            obtain.ControllerCustomTokenSync.as_view(),
            name='token_custom_sync_auth',
        ),
    ],
    tags=['token_auth'],
)
