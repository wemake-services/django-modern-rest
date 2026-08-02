from dmr.routing import Router, path
from server.apps.token_custom_user import views

router = Router(
    'token-custom-user/',
    [
        path(
            'user-sync/',
            views.ControllerWithApiTokenSyncAuth.as_view(),
            name='api_token_sync_auth',
        ),
        path(
            'user-async/',
            views.ControllerWithApiTokenAsyncAuth.as_view(),
            name='api_token_async_auth',
        ),
    ],
)
