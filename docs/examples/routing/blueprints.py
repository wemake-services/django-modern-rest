from django.urls import include, path

from django_modern_rest.routing import Router, compose_blueprints
from examples.using_controller.blueprints import (
    UserCreateBlueprint,
    UserListBlueprint,
)

router = Router([
    path(
        'user/',
        compose_blueprints(
            UserCreateBlueprint,
            UserListBlueprint,
            # Can compose as many blueprints as you need!
        ).as_view(),
        name='users',
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'server'), namespace='api')),
]
