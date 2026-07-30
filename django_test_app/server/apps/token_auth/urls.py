from dmr.routing import Router, path
from server.apps.token_auth import views

router = Router(
    'token-auth/',
    [
        path(
            'token-sync-auth/',
            views.ControllerWithTokenSyncAuth.as_view(),
            name='token_sync_auth',
        ),
    ],
)
