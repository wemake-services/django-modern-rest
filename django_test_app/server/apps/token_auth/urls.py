from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path
from dmr.security.token import concrete_views
from server.apps.token_auth.models import CustomToken
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
        # Both required fields are given here, so there is no view class:
        path(
            'token-concrete-obtain-sync/',
            concrete_views.ObtainTokenSyncController.as_view(
                serializer=PydanticFastSerializer,
                token_cls=CustomToken,
            ),
            name='token_concrete_obtain_sync',
        ),
        path(
            'token-concrete-obtain-async/',
            concrete_views.ObtainTokenAsyncController.as_view(
                serializer=PydanticFastSerializer,
            ),
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
