from django.urls import include, path

from dmr.routing import Router
from examples.using_controller.custom_meta import SettingsController

router = Router(
    [
        path(
            'settings/',
            SettingsController.as_view(),
            name='settings',
        ),
    ],
    prefix='api/',
)

urlpatterns = [
    path(router.prefix, include((router.urls, 'server'), namespace='api')),
]
