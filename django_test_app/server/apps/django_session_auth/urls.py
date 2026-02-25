from django.urls import path

from dmr.routing import Router
from server.apps.django_session_auth import views

router = Router(
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
    prefix='django-session-auth/',
)
