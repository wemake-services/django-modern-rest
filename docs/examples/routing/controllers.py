from django.urls import include, path

from django_modern_rest import Router
from examples.using_controller.custom_meta import SettingsController

router = Router([
    path(
        'settings/',
        SettingsController.as_view(),
        name='settings',
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'server'), namespace='api')),
]
