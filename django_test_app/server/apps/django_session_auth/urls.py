from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.django_session import concrete_views
from server.apps.django_session_auth import views

router = Router(
    'django-session-auth/',
    [
        path(
            'django-session-sync/',
            views.SessionSyncController.as_view(),
            name='django_session_sync',
        ),
        path(
            'django-session-async/',
            views.SessionAsyncController.as_view(),
            name='django_session_async',
        ),
        # Concrete views are routed without writing a subclass for them:
        path(
            'django-session-concrete-sync/',
            concrete_views.DjangoSessionSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='django_session_concrete_sync',
        ),
        path(
            'django-session-concrete-async/',
            concrete_views.DjangoSessionAsyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='django_session_concrete_async',
        ),
        path(
            'user-sync/',
            views.UserSyncController.as_view(),
            name='user_session_sync',
        ),
        path(
            'user-async/',
            views.UserAsyncController.as_view(),
            name='user_session_async',
        ),
    ],
    tags=['django_session_auth'],
)
